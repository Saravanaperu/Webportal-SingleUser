import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.api.routes import router as api_router
from app.core.logging import logger
from app.db.session import database, create_tables
from app.services.angel_one import AngelOneConnector
from app.services.risk_manager import RiskManager
from app.services.order_manager import OrderManager
from app.services.strategy import TradingStrategy
from app.services.instrument_manager import instrument_manager
from app.services.market_data_manager import market_data_manager

app = FastAPI(title="Automated Trading Portal")

# Mount static files for CSS, JS, etc.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Jinja2 templates for the dashboard
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup_event():
    """
    Defines the actions to be performed on application startup.
    This includes connecting to the database, initializing all core services,
    and starting the main strategy loop as a background task.
    """
    logger.info("Application startup sequence initiated...")

    # Connect to the database and create tables if they don't exist
    try:
        await database.connect()
        create_tables()
        logger.info("Database connected and tables verified.")
    except Exception as e:
        logger.critical(f"Fatal error connecting to the database: {e}", exc_info=True)
        # Depending on the desired behavior, you might want to exit the app
        return

    # Initialize and connect to the broker
    try:
        connector = AngelOneConnector()
        if not await connector.connect():
            logger.critical("Could not connect to AngelOne broker. Strategy will not start.")
            return

        # Load instrument list
        await instrument_manager.load_instruments(connector.get_rest_client())
        app.state.instrument_manager = instrument_manager

        # Fetch initial account details to bootstrap the Risk Manager
        account_details = await connector.get_account_details()
        equity = account_details.get('balance', 100000.0) if account_details else 100000.0
        if not account_details:
             logger.warning("Failed to fetch account details. Using default equity for RiskManager.")

        # Initialize core services
        risk_manager = RiskManager(account_equity=equity)
        order_manager = OrderManager(connector=connector, risk_manager=risk_manager, instrument_manager=instrument_manager)
        strategy = TradingStrategy(order_manager=order_manager, risk_manager=risk_manager, connector=connector)

        # Store services in app.state to make them accessible from API endpoints
        app.state.risk_manager = risk_manager
        app.state.order_manager = order_manager
        app.state.strategy = strategy
        app.state.market_data_manager = market_data_manager

        # Start the strategy and run it as a background task
        strategy.start()
        app.state.strategy_task = asyncio.create_task(strategy.run())
        logger.info("Core services initialized and strategy background task started.")

        # Start the WebSocket connection in the background
        ws_client = connector.get_ws_client()
        if ws_client:
            from app.core.config import settings
            instrument_symbols = settings.strategy.instruments

            # This mapping is an assumption based on the library's documentation format.
            # It might need adjustment based on the actual `exch_seg` values from the instrument list.
            exchange_map = {"NSE": "nse_cm", "BSE": "bse_cm", "NFO": "nse_fo"}

            tokens_to_subscribe = []
            for symbol in instrument_symbols:
                # Assuming 'NSE' for all instruments as per strategy config.
                exchange = "NSE"
                token = instrument_manager.get_token(symbol, exchange)
                ws_exchange_format = exchange_map.get(exchange.upper())

                if token and ws_exchange_format:
                    tokens_to_subscribe.append(f"{ws_exchange_format}|{token}")
                else:
                    logger.warning(f"Could not find token or exchange format for {symbol}. It will not be subscribed via WebSocket.")

            if tokens_to_subscribe:
                ws_client.set_instrument_tokens(tokens_to_subscribe)
                app.state.ws_client = ws_client # Store client for shutdown
                app.state.websocket_task = asyncio.create_task(ws_client.connect())
                logger.info("WebSocket client connection task started.")

                # Start the market data processing task
                app.state.market_data_task = asyncio.create_task(
                    process_market_data(ws_client.market_data_queue)
                )
                logger.info("Market data processing task started.")

                # Start the order update processing task
                app.state.order_update_task = asyncio.create_task(
                    process_order_updates(app.state.order_manager, ws_client.order_update_queue)
                )
                logger.info("Order update processing task started.")

        logger.info("✅ Trading Portal Started Successfully.")

    except Exception as e:
        logger.critical(f"Fatal error during service initialization: {e}", exc_info=True)


async def process_market_data(queue: asyncio.Queue):
    """
    Continuously processes market data from the WebSocket queue.
    """
    while True:
        try:
            data = await queue.get()
            market_data_manager.update_tick(data)
            queue.task_done()
        except asyncio.CancelledError:
            logger.info("Market data processing task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error processing market data: {e}", exc_info=True)

async def process_order_updates(order_manager: OrderManager, queue: asyncio.Queue):
    """
    Continuously processes order updates from the WebSocket queue.
    """
    while True:
        try:
            update = await queue.get()
            await order_manager.handle_order_update(update)
            queue.task_done()
        except asyncio.CancelledError:
            logger.info("Order update processing task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error processing order update: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Defines actions for graceful application shutdown.
    """
    logger.info("Application shutdown sequence initiated...")
    tasks_to_cancel = ['strategy_task', 'websocket_task', 'market_data_task', 'order_update_task']
    for task_name in tasks_to_cancel:
        if hasattr(app.state, task_name) and not getattr(app.state, task_name).done():
            getattr(app.state, task_name).cancel()
            logger.info(f"{task_name} cancelled.")

    if hasattr(app.state, 'ws_client') and hasattr(app.state.ws_client, 'disconnect'):
         await app.state.ws_client.disconnect()
         logger.info("WebSocket client disconnected.")

    if database.is_connected:
        await database.disconnect()
        logger.info("Database connection closed.")


@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Serves the main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request, "title": "Dashboard"})

# Include the API router
app.include_router(api_router, prefix="/api")
