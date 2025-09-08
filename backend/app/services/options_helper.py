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
