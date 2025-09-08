import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.api.routes import router as api_router
from app.core.logging import logger
from app.db.session import database, create_tables
from app.angel_one_connector import AngelOneConnector
from app.services.risk_manager import RiskManager
from app.services.order_manager import OrderManager
from app.services.strategy import TradingStrategy

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

        # Fetch initial account details to bootstrap the Risk Manager
        account_details = await connector.get_account_details()
        equity = account_details.get('balance', 100000.0) if account_details else 100000.0
        if not account_details:
             logger.warning("Failed to fetch account details. Using default equity for RiskManager.")

        # Initialize core services
        risk_manager = RiskManager(account_equity=equity)
        order_manager = OrderManager(connector=connector, risk_manager=risk_manager)
        strategy = TradingStrategy(order_manager=order_manager, risk_manager=risk_manager)

        # Store services in app.state to make them accessible from API endpoints
        app.state.risk_manager = risk_manager
        app.state.order_manager = order_manager
        app.state.strategy = strategy

        # Start the strategy and run it as a background task
        strategy.start()
        app.state.strategy_task = asyncio.create_task(strategy.run())
        logger.info("Core services initialized and strategy background task started.")

    except Exception as e:
        logger.critical(f"Fatal error during service initialization: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Defines actions for graceful application shutdown.
    """
    logger.info("Application shutdown sequence initiated...")
    if hasattr(app.state, 'strategy_task') and not app.state.strategy_task.done():
        app.state.strategy_task.cancel()
        logger.info("Strategy task cancelled.")

    if database.is_connected:
        await database.disconnect()
        logger.info("Database connection closed.")


@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Serves the main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request, "title": "Dashboard"})

# Include the API router
app.include_router(api_router, prefix="/api")
