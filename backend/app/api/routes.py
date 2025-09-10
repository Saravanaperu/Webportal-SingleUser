import asyncio
import yaml
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Body, HTTPException
from ..core.logging import logger
from .ws_manager import manager as ws_manager
from ..db.session import database
from ..core.config import StrategyConfig
from ..models.trading import HistoricalTrade

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
    """
    Returns a list of internally tracked open positions with live P&L.
    """
    try:
        order_manager = request.app.state.order_manager
        market_data_manager = request.app.state.market_data_manager
    except AttributeError:
        logger.warning("Services not fully initialized, cannot get positions.")
        return {"error": "Services not initialized."}

    open_positions = order_manager.get_open_positions()
    if not open_positions:
        return []
    
    # Fetch all prices concurrently
    import asyncio
    symbols = [pos['symbol'] for pos in open_positions]
    prices = await asyncio.gather(*[market_data_manager.get_latest_price(symbol) for symbol in symbols])
    
    positions_with_pnl = []
    for pos, live_price in zip(open_positions, prices):
        pnl = 0.0
        if live_price:
            entry_price = pos['entry_price']
            qty = pos['qty']
            if pos['side'] == 'BUY':
                pnl = (live_price - entry_price) * qty
            else: # SELL
                pnl = (entry_price - live_price) * qty

        pos_copy = pos.copy()
        pos_copy['live_price'] = live_price or pos['entry_price']
        pos_copy['pnl'] = round(pnl, 2)
        positions_with_pnl.append(pos_copy)

    return positions_with_pnl

@router.get("/trades")
async def get_trades(request: Request):
    """Returns a list of historical trades from the database."""
    query = HistoricalTrade.__table__.select().order_by(HistoricalTrade.exit_time.desc()).limit(50)
    trades = await database.fetch_all(query)
    return [dict(trade) for trade in trades]

@router.post("/strategy/control")
async def control_strategy(request: Request, payload: dict = Body(...)):
    """
    Controls the trading strategy background task. Actions: "start", "stop", "kill".
    """
    action = payload.get("action")
    try:
        strategy = request.app.state.strategy
        risk_manager = request.app.state.risk_manager
        strategy_task = getattr(request.app.state, 'strategy_task', None)

        if action == "start":
            if not strategy.is_running and (strategy_task is None or strategy_task.done()):
                strategy.start()
                # Create a new background task
                request.app.state.strategy_task = asyncio.create_task(strategy.run())
                logger.info("Strategy background task started via API.")
                return {"status": "Strategy started successfully."}
            return {"status": "Strategy is already running."}

        elif action == "stop":
            if strategy.is_running and strategy_task and not strategy_task.done():
                strategy.stop()
                # Cancel the background task
                strategy_task.cancel()
                logger.info("Strategy background task stopped via API.")
                return {"status": "Strategy stopped."}
            return {"status": "Strategy is already stopped or task not found."}

        elif action == "kill":
            await risk_manager.stop_trading("Manual kill switch activated.")
            if strategy.is_running and strategy_task and not strategy_task.done():
                strategy.stop()
                strategy_task.cancel()
                logger.info("Strategy background task KILLED via API.")
            # In a real app, you would also trigger closing all positions.
            # await request.app.state.order_manager.close_all_positions()
            return {"status": "EMERGENCY STOP ACTIVATED. All trading halted."}

        return {"error": "Invalid action. Use 'start', 'stop', or 'kill'."}
    except AttributeError:
        return {"error": "Services not initialized. Cannot control strategy."}
    except Exception as e:
        logger.error(f"Error in strategy control: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/strategy/parameters", response_model=StrategyConfig)
async def get_strategy_parameters(request: Request):
    """
    Returns the current strategy parameters.
    """
    try:
        strategy = request.app.state.strategy
        return strategy.params
    except AttributeError:
        raise HTTPException(status_code=503, detail="Services not initialized.")

@router.post("/strategy/parameters")
async def set_strategy_parameters(request: Request, params: StrategyConfig):
    """
    Updates the strategy parameters both in the running instance and in config.yaml.
    """
    try:
        # 1. Update the running strategy instance
        strategy = request.app.state.strategy
        strategy.update_parameters(params)

        # 2. Update the config.yaml file
        config_path = "config.yaml"
        try:
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)

            full_config['strategy'] = params.dict()

            with open(config_path, 'w') as f:
                yaml.dump(full_config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Successfully updated {config_path} with new strategy parameters.")

        except Exception as e:
            logger.error(f"Failed to write to {config_path}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to write to config file: {e}")

        return {"status": "success", "message": "Strategy parameters updated successfully."}

    except AttributeError:
        raise HTTPException(status_code=503, detail="Services not initialized.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while setting parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats(request: Request):
    """Returns detailed daily trading statistics."""
    try:
        risk_manager = request.app.state.risk_manager
        market_data_manager = request.app.state.market_data_manager
        stats = {
            "pnl": round(risk_manager.daily_pnl, 2),
            "equity": round(risk_manager.equity, 2),
            "total_trades": risk_manager.total_trades,
            "win_rate": round(risk_manager.win_rate, 2),
            "avg_win_pnl": round(risk_manager.avg_win_pnl, 2),
            "avg_loss_pnl": round(risk_manager.avg_loss_pnl, 2),
            "consecutive_losses": risk_manager.consecutive_losses,
            "is_trading_stopped": risk_manager.is_trading_stopped,
            "last_tick_time": market_data_manager.last_tick_time
        }
        return stats
    except AttributeError:
        return {"error": "Services not initialized. Cannot get stats."}

# === WebSocket Endpoint ===

@router.websocket("/ws/data")
async def websocket_data_endpoint(websocket: WebSocket):
    """
    The single WebSocket endpoint for all real-time data.
    Handles client connection and stays open to receive broadcasted data.
    """
    await ws_manager.connect(websocket)
    logger.info(f"Client connected to WebSocket")
    try:
        while True:
            try:
                # Add timeout to prevent hanging
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        await ws_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}", exc_info=True)
