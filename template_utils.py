from datetime import datetime
from typing import Optional


UNKNOWN_DATE_TEXT = "Unknown date"


def safe_date(value: Optional[str]) -> str:
    """Format an article timestamp as 'Month Day' with safe fallback handling."""
    if not value:
        return UNKNOWN_DATE_TEXT

    value_text = str(value).strip()
    if not value_text:
        return UNKNOWN_DATE_TEXT

    date_text = value_text.split(" ")[0]

    try:
        parsed_date = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return UNKNOWN_DATE_TEXT

    return f"{parsed_date.strftime('%B')} {parsed_date.day}"
