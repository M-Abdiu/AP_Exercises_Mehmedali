from datetime import timedelta

def date_to_calendar_week(date):
    """Convert a date to a calendar week."""
    return date.isocalendar()[1]

def add_days_to_date(date, n):
    """Add n days to a date."""
    return date + timedelta(days=n)
