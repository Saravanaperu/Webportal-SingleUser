from datetime import date, timedelta

def get_current_weekly_expiry() -> date:
    """
    Calculates the current week's Thursday expiry date.
    If today is Thursday, it returns today's date.
    If today is after Thursday, it returns next Thursday's date.
    """
    today = date.today()
    days_to_thursday = (3 - today.weekday() + 7) % 7
    expiry_date = today + timedelta(days=days_to_thursday)
    return expiry_date

def get_atm_strike(spot_price: float, strike_interval: int) -> int:
    """
    Calculates the At-The-Money (ATM) strike price.
    """
    return round(spot_price / strike_interval) * strike_interval

def generate_option_symbol(underlying: str, expiry_date: date, strike: int, option_type: str) -> str:
    """
    Generates the tradable option symbol in the format required by Angel One.
    Example: NIFTY27JUL2319800CE
    """
    underlying_upper = underlying.upper()
    day = expiry_date.strftime('%d')
    month_upper = expiry_date.strftime('%b').upper()
    year_short = expiry_date.strftime('%y')

    # Note: This format is an educated guess based on common broker formats.
    # It may need to be adjusted based on the exact format in the instrument master file.
    return f"{underlying_upper}{day}{month_upper}{year_short}{strike}{option_type.upper()}"

async def get_strike_by_delta(underlying: str, expiry_date: date, target_delta: float, connector) -> tuple[int | None, int | None]:
    """
    Finds the call and put strike prices with deltas closest to the target delta.
    Returns a tuple of (call_strike, put_strike).
    """
    expiry_str = expiry_date.strftime('%d%b%Y').upper()
    option_chain = await connector.get_option_chain(underlying, expiry_str)

    if not option_chain:
        return None, None

    call_options = [opt for opt in option_chain if opt['op_type'] == 'CE']
    put_options = [opt for opt in option_chain if opt['op_type'] == 'PE']

    if not call_options or not put_options:
        return None, None

    closest_call = min(call_options, key=lambda x: abs(float(x.get('delta', 1.0)) - target_delta))
    closest_put = min(put_options, key=lambda x: abs(abs(float(x.get('delta', -1.0))) - target_delta))

    call_strike = int(float(closest_call['strikePrice'])) if closest_call else None
    put_strike = int(float(closest_put['strikePrice'])) if closest_put else None

    return call_strike, put_strike
