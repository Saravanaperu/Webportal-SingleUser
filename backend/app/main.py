import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .api.routes import router as api_router
from .api.ws_manager import manager as ws_manager
from .core.logging import logger
from .db.session import database, create_tables
from .services.angel_one import AngelOneConnector
from .services.risk_manager import RiskManager
from .services.order_manager import OrderManager
from .services.strategy import TradingStrategy
from .services.instrument_manager import instrument_manager
from .services.market_data_manager import market_data_manager

app = FastAPI(title="Automated Trading Portal")

# --- Path Setup ---
# Get the absolute path to the directory containing this file (main.py)
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"


# Mount static files for CSS, JS, etc.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup Jinja2 templates for the dashboard
templates = Jinja2Templates(directory=TEMPLATES_DIR)

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
        app.state.ws_manager = ws_manager # Add manager to state

        # The strategy is no longer started automatically.
        # The user must start it via the API endpoint.
        app.state.strategy_task = None # Explicitly set to None on startup
        logger.info("Core services initialized. Strategy is ready to be started by the user.")

        # Start the WebSocket connection in the background
        ws_client = connector.get_ws_client()
        if ws_client:
            from .core.config import settings
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
                    process_market_data(ws_client.market_data_queue, ws_manager)
                )
                logger.info("Market data processing task started.")

                # Start the order update processing task
                app.state.order_update_task = asyncio.create_task(
                    process_order_updates(app.state.order_manager, ws_client.order_update_queue, ws_manager)
                )
                logger.info("Order update processing task started.")

            # Start the session refresh task
            app.state.refresh_task = asyncio.create_task(
                refresh_connection_periodically(connector, app.state)
            )
            logger.info("Session refresh task started.")

        logger.info("✅ Trading Portal Started Successfully.")

    except Exception as e:
        logger.critical(f"Fatal error during service initialization: {e}", exc_info=True)


async def process_market_data(queue: asyncio.Queue, manager: "WebSocketManager"):
    """
    Continuously processes market data from the WebSocket queue and broadcasts it.
    """
    while True:
        try:
            data = await queue.get()
            # The tick data from the broker is often a list of dicts or a dict.
            # We process it and then broadcast a standardized format.
            market_data_manager.update_tick(data)

            # Let's assume `update_tick` returns a standardized dict for the frontend.
            # For this example, we'll just re-broadcast the raw data under a 'market' type.
            # In a real app, you might want to standardize this.
            await manager.broadcast({"type": "market_data", "data": data})

            queue.task_done()
        except asyncio.CancelledError:
            logger.info("Market data processing task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error processing market data: {e}", exc_info=True)

async def refresh_connection_periodically(connector: AngelOneConnector, app_state):
    """
    Periodically reconnects to the broker to refresh the session token.
    """
    while True:
        try:
            # Sleep for 23.5 hours
            sleep_duration = 23.5 * 60 * 60
            logger.info(f"Session refresher is sleeping for {sleep_duration / 3600:.1f} hours.")
            await asyncio.sleep(sleep_duration)

            logger.info("Attempting to refresh broker session...")
            is_success = await connector.reconnect()

            if is_success:
                # If reconnection is successful, we need to restart the WebSocket client
                logger.info("Restarting WebSocket client after session refresh...")

                # 1. Cancel the old tasks
                if hasattr(app_state, 'websocket_task') and not app_state.websocket_task.done():
                    app_state.websocket_task.cancel()
                if hasattr(app_state, 'market_data_task') and not app_state.market_data_task.done():
                    app_state.market_data_task.cancel()
                if hasattr(app_state, 'order_update_task') and not app_state.order_update_task.done():
                    app_state.order_update_task.cancel()

                # 2. Start new tasks with the new ws_client instance
                ws_client = connector.get_ws_client()
                if ws_client:
                    from .core.config import settings
                    instrument_symbols = settings.strategy.instruments
                    exchange_map = {"NSE": "nse_cm", "BSE": "bse_cm", "NFO": "nse_fo"}

                    tokens_to_subscribe = []
                    for symbol in instrument_symbols:
                        exchange = "NSE"
                        token = instrument_manager.get_token(symbol, exchange)
                        ws_exchange_format = exchange_map.get(exchange.upper())

                        if token and ws_exchange_format:
                            tokens_to_subscribe.append(f"{ws_exchange_format}|{token}")
                        else:
                            logger.warning(f"Could not find token or format for {symbol} during reconnect.")

                    ws_client.set_instrument_tokens(tokens_to_subscribe)
                    app_state.ws_client = ws_client
                    app_state.websocket_task = asyncio.create_task(ws_client.connect())
                    app_state.market_data_task = asyncio.create_task(process_market_data(ws_client.market_data_queue, app_state.ws_manager))
                    app_state.order_update_task = asyncio.create_task(process_order_updates(app_state.order_manager, ws_client.order_update_queue, app_state.ws_manager))
                    logger.info("WebSocket client and data processors restarted successfully.")
            else:
                logger.error("Session refresh failed. Will retry in 1 hour.")
                await asyncio.sleep(3600) # Sleep for an hour before retrying

        except asyncio.CancelledError:
            logger.info("Connection refresher task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in connection refresher: {e}", exc_info=True)
            await asyncio.sleep(3600) # Wait for an hour on unexpected error


async def process_order_updates(order_manager: OrderManager, queue: asyncio.Queue, manager: "WebSocketManager"):
    """
    Continuously processes order updates from the WebSocket queue and broadcasts them.
    """
    while True:
        try:
            update = await queue.get()
            # The order manager handles the update internally
            await order_manager.handle_order_update(update)

            # Broadcast the update to all connected clients
            await manager.broadcast({"type": "order_update", "data": update})

            # Additionally, since an order update can affect P&L and stats,
            # let's re-fetch and broadcast the latest stats.
            risk_manager = order_manager.risk_manager
            stats = {
                "pnl": round(risk_manager.daily_pnl, 2),
                "equity": round(risk_manager.equity, 2),
                "total_trades": risk_manager.total_trades,
                "win_rate": round(risk_manager.win_rate, 2),
                "avg_win_pnl": round(risk_manager.avg_win_pnl, 2),
                "avg_loss_pnl": round(risk_manager.avg_loss_pnl, 2),
                "is_trading_stopped": risk_manager.is_trading_stopped,
            }
            await manager.broadcast({"type": "stats_update", "data": stats})


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
    tasks_to_cancel = ['strategy_task', 'websocket_task', 'market_data_task', 'order_update_task', 'refresh_task']
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
