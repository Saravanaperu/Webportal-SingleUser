import asyncio
import yaml
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Body, HTTPException
from ..core.logging import logger
from .ws_manager import manager as ws_manager
from ..db.session import database
from ..core.config import StrategyConfig
from ..models.trading import HistoricalTrade
from ..services.cache_manager import cache_manager
from ..services.backtest_engine import backtest_engine

router = APIRouter()

# In-memory log storage
log_buffer = []
MAX_LOGS = 100

# Cache for broker data to avoid rate limits
data_cache = {}
CACHE_DURATION = 30  # seconds - increased to reduce API calls
last_broker_call = {}
MIN_CALL_INTERVAL = 2  # minimum seconds between broker calls

# Production-ready broker connection management
broker_state = {
    'last_successful_call': 0,
    'consecutive_failures': 0,
    'backoff_until': 0,
    'max_calls_per_minute': 10,
    'call_timestamps': []
}

def add_log(level, message):
    """Add log entry to buffer"""
    global log_buffer
    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message
    }
    log_buffer.append(log_entry)
    if len(log_buffer) > MAX_LOGS:
        log_buffer.pop(0)
    
    # Also log to backend console
    if level.lower() == 'error':
        logger.error(message)
    elif level.lower() == 'warning':
        logger.warning(message)
    else:
        logger.info(message)

# Initialize with startup logs
add_log("info", "Trading Portal API initialized")
add_log("info", "Waiting for broker connection...")

# === Paper Trading Endpoints ===

@router.post("/paper-trading/toggle")
async def toggle_paper_trading(payload: dict = Body(...)):
    """Toggle paper trading mode on/off"""
    from ..services.paper_trading import paper_trading_manager
    
    action = payload.get("action")
    if action == "enable":
        paper_trading_manager.enable_paper_trading()
        return {"status": "Paper trading enabled", "mode": "paper"}
    elif action == "disable":
        paper_trading_manager.disable_paper_trading()
        return {"status": "Paper trading disabled", "mode": "live"}
    elif action == "reset":
        paper_trading_manager.reset_paper_account()
        return {"status": "Paper account reset"}
    else:
        return {"error": "Invalid action"}

@router.get("/paper-trading/status")
async def get_paper_trading_status():
    """Get paper trading status and stats"""
    from ..services.paper_trading import paper_trading_manager
    
    return {
        "is_paper_mode": paper_trading_manager.is_paper_mode,
        "stats": paper_trading_manager.get_paper_stats(),
        "positions": paper_trading_manager.get_paper_positions(),
        "trades": paper_trading_manager.get_paper_trades()[-10:]  # Last 10 trades
    }

# === REST Endpoints ===

@router.get("/system/health")
async def get_system_health(request: Request):
    """Returns system health status and issues"""
    issues = []
    
    try:
        # Check broker connection
        if not (hasattr(request.app.state, 'order_manager') and 
                request.app.state.order_manager and 
                hasattr(request.app.state.order_manager, 'connector') and
                request.app.state.order_manager.connector):
            issues.append({
                'severity': 'error',
                'message': 'Broker connection not available'
            })
        
        # Check strategy status
        if hasattr(request.app.state, 'strategy') and request.app.state.strategy:
            if not request.app.state.strategy.is_running:
                issues.append({
                    'severity': 'warning', 
                    'message': 'Trading strategy is not running'
                })
        
        # Check market data feed
        if hasattr(request.app.state, 'market_data_manager') and request.app.state.market_data_manager:
            try:
                last_tick = request.app.state.market_data_manager.get_last_tick_time()
                if not last_tick or (datetime.utcnow() - last_tick).total_seconds() > 60:
                    issues.append({
                        'severity': 'warning',
                        'message': 'Market data feed may be stale'
                    })
            except:
                pass
        
        return {'issues': issues}
        
    except Exception as e:
        return {'issues': [{'severity': 'error', 'message': f'Health check failed: {str(e)}'}]}

@router.post("/backtest/run")
async def run_backtest(params: dict = Body(...)):
    """Run strategy backtest"""
    try:
        results = await backtest_engine.run_backtest(params)
        return results
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        return {"error": str(e)}

def can_make_broker_call():
    """Production rate limiting for broker API calls"""
    current_time = datetime.now().timestamp()
    
    # Check backoff period
    if current_time < broker_state['backoff_until']:
        return False
    
    # Clean old timestamps (older than 1 minute)
    broker_state['call_timestamps'] = [
        ts for ts in broker_state['call_timestamps'] 
        if current_time - ts < 60
    ]
    
    # Check rate limit
    if len(broker_state['call_timestamps']) >= broker_state['max_calls_per_minute']:
        return False
    
    return True

def record_broker_call_result(success: bool):
    """Record broker call result for rate limiting"""
    current_time = datetime.now().timestamp()
    broker_state['call_timestamps'].append(current_time)
    
    if success:
        broker_state['last_successful_call'] = current_time
        broker_state['consecutive_failures'] = 0
    else:
        broker_state['consecutive_failures'] += 1
        # Exponential backoff: 30s, 60s, 120s, 300s
        backoff_seconds = min(30 * (2 ** broker_state['consecutive_failures']), 300)
        broker_state['backoff_until'] = current_time + backoff_seconds

@router.get("/indices")
async def get_indices(request: Request):
    """Returns real-time indices data with caching."""
    async def fetch_indices():
        from ..services.tick_data_manager import tick_data_manager
        
        # Try database first during market hours
        if tick_data_manager.is_market_hours():
            indices = {}
            symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
            
            for symbol in symbols:
                db_data = await tick_data_manager.get_latest_ltp(symbol)
                if db_data:
                    indices[symbol] = {
                        "price": db_data['ltp'],
                        "change": db_data['change'],
                        "changePercent": db_data['change_percent']
                    }
            
            if indices:
                return indices
        
        # Fallback to broker API
        if not (hasattr(request.app.state, 'order_manager') and 
                request.app.state.order_manager and 
                hasattr(request.app.state.order_manager, 'connector') and
                request.app.state.order_manager.connector):
            return {"error": "Broker services not available"}
        
        if not can_make_broker_call():
            return {"error": "Rate limited"}
        
        try:
            connector = request.app.state.order_manager.connector
            indices = {}
            symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
            
            for symbol in symbols:
                quote_data = await connector.get_quote(symbol)
                if quote_data and quote_data.get('ltp', 0) > 0:
                    indices[symbol] = {
                        "price": float(quote_data.get('ltp', 0)),
                        "change": float(quote_data.get('change', 0)),
                        "changePercent": float(quote_data.get('pChange', 0))
                    }
                else:
                    indices[symbol] = {"error": f"No data for {symbol}"}
            
            record_broker_call_result(True)
            return indices
            
        except Exception as e:
            record_broker_call_result(False)
            logger.error(f"Error fetching indices: {e}")
            return {"error": f"Broker connection failed: {str(e)}"}
    
    result = await cache_manager.get_or_fetch("indices_data", fetch_indices, ttl=10)
    
    # If still no data, return default values
    if not result or result.get('error'):
        return {
            "NIFTY": {"price": 24500, "change": 0, "changePercent": 0},
            "BANKNIFTY": {"price": 51000, "change": 0, "changePercent": 0},
            "FINNIFTY": {"price": 23000, "change": 0, "changePercent": 0}
        }
    
    return result

@router.get("/options-chain/{symbol}")
async def get_options_chain(symbol: str):
    """Returns options chain from cache or calculated."""
    # Try cache first (background task keeps it updated)
    cached_options = await cache_manager.get(f"options_{symbol}")
    if cached_options:
        return cached_options
    
    # Fallback: calculate with default spot prices
    default_prices = {"NIFTY": 24500, "BANKNIFTY": 51000, "FINNIFTY": 23000}
    spot_price = default_prices.get(symbol, 25000)
    
    from ..services.background_tasks import background_task_manager
    options_chain = background_task_manager._calculate_options_chain(symbol, spot_price)
    
    # Cache the calculated chain
    await cache_manager.set(f"options_{symbol}", options_chain, ttl=30)
    
    return options_chain

@router.get("/options-chain/{symbol}")
async def get_options_chain(symbol: str, request: Request):
    """Returns options chain from database during market hours, calculated otherwise"""
    from ..services.tick_data_manager import tick_data_manager
    
    cache_key = f"options_{symbol}"
    current_time = datetime.now().timestamp()
    
    # During market hours, try to get options data from database
    if tick_data_manager.is_market_hours():
        db_options = await tick_data_manager.get_options_chain_from_db(symbol)
        if db_options:
            return db_options
    
    # Return cached data if available and fresh
    if (cache_key in data_cache and 
        current_time - data_cache[cache_key]['timestamp'] < CACHE_DURATION):
        return data_cache[cache_key]['data']
    
    # Get live spot price from indices
    spot_price = None
    indices_cache = data_cache.get('indices_data', {})
    if (indices_cache and 
        symbol in indices_cache.get('data', {}) and 
        'price' in indices_cache['data'][symbol]):
        spot_price = indices_cache['data'][symbol]['price']
    
    # Try to get spot from database if not in cache
    if not spot_price:
        db_data = await tick_data_manager.get_latest_ltp(symbol)
        if db_data:
            spot_price = db_data['ltp']
    
    if not spot_price:
        return {"error": f"No spot price available for {symbol}"}
    
    # Generate options chain based on live spot price with proper intervals
    if symbol == "BANKNIFTY":
        strike_interval = 100
    elif symbol == "FINNIFTY":
        strike_interval = 50
    else:  # NIFTY
        strike_interval = 50
    
    atm_strike = round(spot_price / strike_interval) * strike_interval
    strikes = [atm_strike + (i * strike_interval) for i in range(-5, 6)]
    
    options_data = []
    for i, strike in enumerate(strikes):
        distance_from_atm = abs(i - 5)
        
        # Calculate realistic option prices based on live spot and symbol
        price_multiplier = 0.0025 if symbol == "BANKNIFTY" else 0.002
        min_premium = 8 if symbol == "BANKNIFTY" else 5
        
        if distance_from_atm == 0:  # ATM
            call_ltp = max(min_premium, spot_price * price_multiplier)
            put_ltp = max(min_premium, spot_price * price_multiplier)
        elif i < 5:  # ITM calls, OTM puts
            intrinsic_call = max(0, spot_price - strike)
            time_value_call = spot_price * (price_multiplier * 0.5)
            call_ltp = max(min_premium, intrinsic_call + time_value_call)
            put_ltp = max(min_premium, spot_price * price_multiplier * 0.5 * (distance_from_atm + 1))
        else:  # OTM calls, ITM puts
            call_ltp = max(min_premium, spot_price * price_multiplier * 0.5 * (distance_from_atm + 1))
            intrinsic_put = max(0, strike - spot_price)
            time_value_put = spot_price * (price_multiplier * 0.5)
            put_ltp = max(min_premium, intrinsic_put + time_value_put)
        
        # Volume and OI based on symbol and distance from ATM - current market levels
        if symbol == "BANKNIFTY":
            base_volume = 120000 - (distance_from_atm * 15000)
            base_oi = 200000 - (distance_from_atm * 25000)
        elif symbol == "NIFTY":
            base_volume = 90000 - (distance_from_atm * 12000)
            base_oi = 180000 - (distance_from_atm * 22000)
        else:  # FINNIFTY
            base_volume = 60000 - (distance_from_atm * 10000)
            base_oi = 120000 - (distance_from_atm * 15000)
        
        options_data.append({
            "strike": strike,
            "call": {
                "ltp": round(call_ltp, 2),
                "volume": max(5000, base_volume),
                "oi": max(10000, base_oi),
                "iv": round(15 + (distance_from_atm * 2.5), 1)
            },
            "put": {
                "ltp": round(put_ltp, 2),
                "volume": max(4000, base_volume - 5000),
                "oi": max(8000, base_oi - 10000),
                "iv": round(15 + (distance_from_atm * 2.5), 1)
            }
        })
    
    data_cache[cache_key] = {'data': options_data, 'timestamp': current_time}
    return options_data

@router.get("/broker/details")
async def get_broker_details(request: Request):
    """Returns comprehensive broker connection details"""
    try:
        # Check if services are initialized
        if (hasattr(request.app.state, 'order_manager') and 
            request.app.state.order_manager and 
            hasattr(request.app.state.order_manager, 'connector')):
            
            connector = request.app.state.order_manager.connector
            if not connector:
                add_log("error", "Broker connector not initialized")
                return {
                    "status": "DISCONNECTED",
                    "error": "Connector not initialized",
                    "broker_name": "Angel One",
                    "api_version": "N/A"
                }
            
            # Test connection
            account_details = await connector.get_account_details()
            
            if account_details:
                add_log("info", f"Broker connection verified - Balance: ₹{account_details.get('balance', 0)}")
                
                # Check if WebSocket is connected and has subscribed tokens
                ws_client = getattr(request.app.state, 'ws_client', None)
                websocket_connected = bool(ws_client and hasattr(ws_client, 'ws') and ws_client.ws)
                
                # Check if tokens are subscribed (market feed active)
                tokens_subscribed = bool(getattr(request.app.state, 'tokens_to_subscribe', []))
                market_feed_active = websocket_connected and tokens_subscribed
                
                return {
                    "status": "CONNECTED",
                    "broker_name": "Angel One",
                    "api_version": "1.5.5",
                    "session_token": bool(getattr(connector, 'session_token', None)),
                    "feed_token": bool(getattr(connector, 'feed_token', None)),
                    "client_id": getattr(connector, 'client_id', 'N/A'),
                    "last_heartbeat": datetime.now().strftime("%H:%M:%S"),
                    "connection_time": getattr(connector, 'connection_time', 'N/A'),
                    "market_feed_active": market_feed_active,
                    "websocket_connected": websocket_connected,
                    "account_balance": account_details.get('balance', 0)
                }
            else:
                add_log("error", "Broker connection test failed - no account data received")
                return {
                    "status": "DISCONNECTED",
                    "error": "Failed to fetch account details",
                    "broker_name": "Angel One",
                    "api_version": "1.5.5"
                }
        else:
            add_log("warning", "Services not initialized yet")
            return {
                "status": "INITIALIZING",
                "error": "Services still initializing",
                "broker_name": "Angel One",
                "api_version": "1.5.5"
            }
            
    except Exception as e:
        add_log("error", f"Broker connection error: {str(e)}")
        logger.error(f"Broker connection error: {e}")
        return {
            "status": "DISCONNECTED",
            "error": str(e),
            "broker_name": "Angel One",
            "api_version": "1.5.5"
        }

@router.get("/broker/status")
async def get_broker_status(request: Request):
    """Returns detailed broker connection status"""
    try:
        # Check if services are initialized
        if (hasattr(request.app.state, 'order_manager') and 
            request.app.state.order_manager and 
            hasattr(request.app.state.order_manager, 'connector')):
            
            connector = request.app.state.order_manager.connector
            if not connector:
                return {"connected": False, "error": "Connector not initialized"}
            
            # Test connection by fetching account details
            account_details = await connector.get_account_details()
            
            if account_details:
                # Check WebSocket and token subscription status
                ws_client = getattr(request.app.state, 'ws_client', None)
                websocket_connected = bool(ws_client and hasattr(ws_client, 'ws') and ws_client.ws)
                tokens_subscribed = bool(getattr(request.app.state, 'tokens_to_subscribe', []))
                
                return {
                    "connected": True,
                    "session_id": getattr(connector, 'session_id', 'N/A'),
                    "user_id": getattr(connector, 'user_id', 'N/A'),
                    "last_update": datetime.now().strftime("%H:%M:%S"),
                    "market_data_active": websocket_connected and tokens_subscribed,
                    "websocket_connected": websocket_connected,
                    "account_balance": account_details.get('balance', 0)
                }
            else:
                return {"connected": False, "error": "Failed to fetch account details"}
        else:
            return {"connected": False, "error": "Services not initialized"}
            
    except Exception as e:
        add_log("error", f"Broker status check failed: {str(e)}")
        logger.error(f"Broker status check failed: {e}")
        return {"connected": False, "error": str(e)}

@router.get("/account")
async def get_account(request: Request):
    """Returns real-time account details with caching."""
    # Check if paper trading mode
    from ..services.paper_trading import paper_trading_manager
    if paper_trading_manager.is_paper_mode:
        stats = paper_trading_manager.get_paper_stats()
        return {
            "balance": stats['current_balance'],
            "margin": 0,
            "available": stats['current_balance'],
            "paper_mode": True
        }
    
    async def fetch_account():
        if not (hasattr(request.app.state, 'order_manager') and 
                request.app.state.order_manager and 
                hasattr(request.app.state.order_manager, 'connector') and
                request.app.state.order_manager.connector):
            return {"error": "Broker services not available"}
        
        if not can_make_broker_call():
            return {"error": "Rate limited"}
        
        try:
            connector = request.app.state.order_manager.connector
            details = await connector.get_account_details()
            if details:
                record_broker_call_result(True)
                return details
            else:
                record_broker_call_result(False)
                return {"error": "No account data received"}
        except Exception as e:
            record_broker_call_result(False)
            logger.error(f"Error fetching account details: {e}")
            return {"error": f"Account fetch failed: {str(e)}"}
    
    return await cache_manager.get_or_fetch("account_data", fetch_account, ttl=60)

@router.get("/positions")
async def get_positions(request: Request):
    """Returns cached positions with live P&L."""
    # Try cache first (background task keeps it updated)
    cached_positions = await cache_manager.get("positions_data")
    if cached_positions:
        return cached_positions
    
    # Fallback to direct calculation
    try:
        if (hasattr(request.app.state, 'order_manager') and 
            request.app.state.order_manager and
            hasattr(request.app.state, 'market_data_manager') and
            request.app.state.market_data_manager):
            
            order_manager = request.app.state.order_manager
            market_data_manager = request.app.state.market_data_manager
            
            open_positions = order_manager.get_open_positions()
            if not open_positions:
                return []
            
            # Fetch all prices concurrently
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
                    else:
                        pnl = (entry_price - live_price) * qty

                pos_copy = pos.copy()
                pos_copy['live_price'] = live_price or pos['entry_price']
                pos_copy['pnl'] = round(pnl, 2)
                positions_with_pnl.append(pos_copy)

            return positions_with_pnl
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []

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
            add_log("info", "Attempting to start trading strategy...")
            if not strategy.is_running and (strategy_task is None or strategy_task.done()):
                strategy.start()
                # Create a new background task
                request.app.state.strategy_task = asyncio.create_task(strategy.run())
                add_log("info", "Trading strategy started successfully")
                logger.info("Strategy background task started via API.")
                return {"status": "Strategy started successfully."}
            add_log("warning", "Strategy is already running")
            return {"status": "Strategy is already running."}

        elif action == "stop":
            add_log("info", "Attempting to stop trading strategy...")
            if strategy.is_running and strategy_task and not strategy_task.done():
                strategy.stop()
                # Cancel the background task
                strategy_task.cancel()
                add_log("info", "Trading strategy stopped successfully")
                logger.info("Strategy background task stopped via API.")
                return {"status": "Strategy stopped."}
            add_log("warning", "Strategy is already stopped")
            return {"status": "Strategy is already stopped or task not found."}

        elif action == "kill":
            add_log("warning", "EMERGENCY STOP activated - halting all trading")
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
        add_log("error", "Services not initialized - cannot control strategy")
        return {"error": "Services not initialized. Cannot control strategy."}
    except Exception as e:
        add_log("error", f"Error in strategy control: {str(e)}")
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
        add_log("info", "Updating strategy parameters...")
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

            add_log("info", "Strategy parameters updated successfully")
            logger.info(f"Successfully updated {config_path} with new strategy parameters.")

        except Exception as e:
            add_log("error", f"Failed to write to config file: {str(e)}")
            logger.error(f"Failed to write to {config_path}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to write to config file: {e}")

        return {"status": "success", "message": "Strategy parameters updated successfully."}

    except AttributeError:
        raise HTTPException(status_code=503, detail="Services not initialized.")
    except Exception as e:
        add_log("error", f"Error updating parameters: {str(e)}")
        logger.error(f"An unexpected error occurred while setting parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats(request: Request):
    """
    Returns a comprehensive overview of trading statistics, account status,
    and application health.
    """
    try:
        # Check if all services are initialized
        if (hasattr(request.app.state, 'risk_manager') and 
            hasattr(request.app.state, 'market_data_manager') and
            hasattr(request.app.state, 'strategy') and
            hasattr(request.app.state, 'order_manager') and
            request.app.state.risk_manager and
            request.app.state.market_data_manager and
            request.app.state.strategy and
            request.app.state.order_manager):
            
            # --- Service Access ---
            risk_manager = request.app.state.risk_manager
            market_data_manager = request.app.state.market_data_manager
            strategy = request.app.state.strategy
            order_manager = request.app.state.order_manager

            # --- Data Calculation ---
            # 1. Account Details
            balance = 0.0
            margin = 0.0
            try:
                if hasattr(order_manager, 'connector') and order_manager.connector:
                    account_details = await order_manager.connector.get_account_details()
                    balance = account_details.get('balance', 0.0) if account_details else 0.0
                    margin = account_details.get('margin', 0.0) if account_details else 0.0
            except Exception as e:
                add_log("warning", f"Could not fetch account details: {str(e)}")

            # 2. Data Feed Status
            is_feed_connected = False
            try:
                last_tick = market_data_manager.get_last_tick_time()
                if last_tick:
                    # Check if the last tick was within the last 15 seconds
                    time_diff = (datetime.utcnow() - last_tick).total_seconds()
                    if time_diff < 15:
                        is_feed_connected = True
            except Exception as e:
                add_log("warning", f"Could not check data feed status: {str(e)}")

            # --- Response Assembly ---
            stats = {
                # Account Info
                "balance": round(balance, 2),
                "margin": round(margin, 2),

                # Performance Stats
                "realized_pnl": round(risk_manager.daily_pnl, 2),
                "total_trades": risk_manager.total_trades,
                "win_rate": round(risk_manager.win_rate, 2),
                "avg_win": round(risk_manager.avg_win_pnl, 2),
                "avg_loss": round(risk_manager.avg_loss_pnl, 2),

                # System Status
                "is_strategy_running": strategy.is_running,
                "data_feed_connected": is_feed_connected,
                "websocket_connected": bool(getattr(request.app.state, 'ws_client', None)),
                "market_feed_active": bool(getattr(request.app.state, 'tokens_to_subscribe', [])),
            }
            return stats
        else:
            # Services not fully initialized, return default state
            return {
                "balance": 0, "margin": 0, "realized_pnl": 0,
                "total_trades": 0, "win_rate": 0, "avg_win": 0, "avg_loss": 0,
                "is_strategy_running": False, "data_feed_connected": False,
                "websocket_connected": False, "market_feed_active": False,
                "error": "Services not fully initialized."
            }
            
    except Exception as e:
        add_log("error", f"Error fetching stats: {str(e)}")
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        return {
            "balance": 0, "margin": 0, "realized_pnl": 0,
            "total_trades": 0, "win_rate": 0, "avg_win": 0, "avg_loss": 0,
            "is_strategy_running": False, "data_feed_connected": False,
            "websocket_connected": False, "market_feed_active": False,
            "error": "Failed to fetch statistics."
        }

# === WebSocket Endpoints ===

@router.websocket("/ws/data")
async def websocket_data_endpoint(websocket: WebSocket):
    """Legacy WebSocket endpoint for compatibility."""
    await ws_manager.connect(websocket)
    add_log("info", "WebSocket client connected")
    logger.info(f"Client connected to WebSocket")
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        add_log("info", "WebSocket client disconnected")
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        await ws_manager.disconnect(websocket)
        add_log("error", f"WebSocket error: {str(e)}")
        logger.error(f"WebSocket error: {e}", exc_info=True)

@router.websocket("/ws/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket):
    """Real-time data WebSocket with 500ms updates."""
    await websocket.accept()
    logger.info("Real-time WebSocket client connected")
    
    try:
        while True:
            # Get live data from cache
            account_data = await cache_manager.get("account_data")
            positions_data = await cache_manager.get("positions_data")
            indices_data = await cache_manager.get("indices_data")
            
            # Send combined data
            await websocket.send_json({
                "type": "realtime_update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "account": account_data,
                    "positions": positions_data or [],
                    "indices": indices_data or {},
                    "stats": {
                        "balance": account_data.get('balance', 0) if account_data else 0,
                        "realized_pnl": 0,
                        "total_trades": 0,
                        "win_rate": 0,
                        "is_strategy_running": False,
                        "data_feed_connected": True
                    }
                }
            })
            
            await asyncio.sleep(0.5)  # 500ms updates
            
    except WebSocketDisconnect:
        logger.info("Real-time WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Real-time WebSocket error: {e}", exc_info=True)