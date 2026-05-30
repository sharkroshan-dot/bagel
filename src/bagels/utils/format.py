from datetime import datetime, timedelta

import bagels.config as config


def parse_formula_expression(value: str) -> float:
    # parse value formula expression. Assumes valid expression
    # fix possible -+123.123 to -123.123
    try:
        value = value.replace("+-", "-")
        # remove ending operators
        if value[-1] in "+-*/.":
            value = value[:-1]
        return round(float(eval(value)), config.CONFIG.defaults.round_decimals)
    except Exception:
        return 0


def format_date_to_readable(date) -> str:
    today = datetime.now().date()
    date = date.date() if isinstance(date, datetime) else date

    if date == today:
        return "Today"
    elif date == today - timedelta(days=1):
        return "Yesterday"

    # Get start of current week (Monday)
    start_of_week = today - timedelta(days=today.weekday())
    # Get end of current week (Sunday)
    end_of_week = start_of_week + timedelta(days=6)

    if start_of_week <= date <= end_of_week:
        return date.strftime("%A")
    else:
        return date.strftime(config.CONFIG.defaults.date_format)


def format_period_to_readable(filter: dict) -> str:
    offset = filter["offset"]
    offset_type = filter["offset_type"]
    first_day_of_week = config.CONFIG.defaults.first_day_of_week
    if offset_type == "day":
        return format_date_to_readable(datetime.now() + timedelta(days=offset))
    match offset:
        case 0:
            return f"This {offset_type.title()}"
        case -1:
            return f"Last {offset_type.title()}"
        case _:
            now = datetime.now()
            match offset_type:
                case "year":
                    target_year = now.year + offset
                    return f"{target_year}"
                case "month":
                    target_month = now.month + offset
                    target_year = now.year + (target_month - 1) // 12
                    target_month = ((target_month - 1) % 12) + 1
                    return f"{datetime(target_year, target_month, 1).strftime('%B %Y')}"
                case "week":
                    target_date = now + timedelta(weeks=offset)
                    # Calculate days to first day of week based on first_day_of_week setting
                    days_to_first = (target_date.weekday() - first_day_of_week) % 7
                    start = target_date - timedelta(days=days_to_first)
                    end = start + timedelta(days=6)
                    return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
                case "day":
                    target_date = now + timedelta(days=offset)
                    return f"{target_date.strftime('%d %B %Y')}"

