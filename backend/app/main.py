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
from app.services.trading_engine import TradingEngine
from app.services.instrument_manager import instrument_manager

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
        engine = TradingEngine(order_manager=order_manager,
                                     risk_manager=risk_manager,
                                     connector=connector,
                                     instrument_manager=instrument_manager)

        # Store services in app.state to make them accessible from API endpoints
        app.state.risk_manager = risk_manager
        app.state.order_manager = order_manager
        app.state.engine = engine

        # Start the engine and run it as a background task
        engine.start()
        app.state.engine_task = asyncio.create_task(engine.run())
        logger.info("Core services initialized and trading engine background task started.")

    except Exception as e:
        logger.critical(f"Fatal error during service initialization: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Defines actions for graceful application shutdown.
    """
    logger.info("Application shutdown sequence initiated...")
    if hasattr(app.state, 'engine_task') and not app.state.engine_task.done():
        app.state.engine_task.cancel()
        logger.info("Trading engine task cancelled.")

    if database.is_connected:
        await database.disconnect()
        logger.info("Database connection closed.")


@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Serves the main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request, "title": "Dashboard"})

# Include the API router
app.include_router(api_router, prefix="/api")
