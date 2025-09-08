import asyncio
import numpy as np
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Body
from app.core.logging import logger
from app.db.session import database

router = APIRouter()

# === REST Endpoints ===

@router.get("/account")
async def get_account(request: Request):
    """Returns account balance and margin by calling the connector."""
    try:
        connector = request.app.state.order_manager.connector
        if connector and connector.rest_client:
            details = await connector.get_account_details()
            return details or {"error": "Could not fetch account details."}
    except AttributeError:
        logger.warning("Services not fully initialized, cannot get account details.")
    return {"error": "Connector not available or services not initialized."}

@router.get("/positions")
async def get_positions(request: Request):
    """Returns open positions."""
    try:
        connector = request.app.state.order_manager.connector
        if connector and connector.rest_client:
            return await connector.get_positions()
    except AttributeError:
        logger.warning("Services not fully initialized, cannot get positions.")
    return {"error": "Connector not available or services not initialized."}

@router.get("/orders")
async def get_orders(request: Request):
    """Returns a list of today's orders from the database."""
    query = "SELECT * FROM orders ORDER BY ts DESC LIMIT 50"
    orders = await database.fetch_all(query)
    return [dict(order) for order in orders]

@router.post("/strategy/control")
async def control_strategy(request: Request, payload: dict = Body(...)):
    """
    Controls the trading strategy. Actions: "start", "stop", "kill".
    """
    action = payload.get("action")
    try:
        strategy = request.app.state.strategy
        risk_manager = request.app.state.risk_manager

        if action == "start":
            if not strategy.is_running:
                strategy.start()
                return {"status": "Strategy started."}
            return {"status": "Strategy is already running."}

        elif action == "stop":
            if strategy.is_running:
                strategy.stop()
                return {"status": "Strategy stopped."}
            return {"status": "Strategy is already stopped."}

        elif action == "kill":
            risk_manager.stop_trading("Manual kill switch activated.")
            strategy.stop()
            # In a real app, you would also trigger closing all positions.
            # await request.app.state.order_manager.close_all_positions()
            return {"status": "EMERGENCY STOP ACTIVATED. All trading halted."}

        return {"error": "Invalid action. Use 'start', 'stop', or 'kill'."}
    except AttributeError:
        return {"error": "Services not initialized. Cannot control strategy."}

@router.get("/stats")
async def get_stats(request: Request):
    """Returns daily trading statistics."""
    try:
        risk_manager = request.app.state.risk_manager
        stats = {
            "pnl": round(risk_manager.daily_pnl, 2),
            "realized_pnl": round(risk_manager.daily_pnl, 2),
            "unrealized_pnl": 0.0,
            "win_rate": None,
            "drawdown": None,
            "consecutive_losses": risk_manager.consecutive_losses,
            "is_trading_stopped": risk_manager.is_trading_stopped
        }
        return stats
    except AttributeError:
        return {"error": "Services not initialized. Cannot get stats."}

# === WebSocket Endpoints ===

@router.websocket("/ws/market")
async def websocket_market_endpoint(websocket: WebSocket):
    """Pushes live simulated tick data to the client."""
    await websocket.accept()
    logger.info("Client connected to market WebSocket.")
    try:
        while True:
            await websocket.send_json({
                "symbol": "NIFTYBEES-EQ",
                "price": round(151.0 + (np.random.randn() * 0.1), 2),
                "ts": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("Client disconnected from market websocket.")
    except Exception as e:
        logger.error(f"Error in market websocket: {e}", exc_info=True)

@router.websocket("/ws/orders")
async def websocket_orders_endpoint(websocket: WebSocket):
    """Pushes order updates to the client by polling the database."""
    await websocket.accept()
    logger.info("Client connected to orders WebSocket.")
    last_order_id = 0
    try:
        while True:
            query = "SELECT * FROM orders WHERE id > :last_id ORDER BY id ASC"
            new_orders = await database.fetch_all(query, values={"last_id": last_order_id})
            if new_orders:
                for order in new_orders:
                    await websocket.send_json(dict(order))
                    last_order_id = order.id
            await asyncio.sleep(3) # Poll every 3 seconds
    except WebSocketDisconnect:
        logger.info("Client disconnected from orders websocket.")
    except Exception as e:
        logger.error(f"Error in orders websocket: {e}", exc_info=True)
