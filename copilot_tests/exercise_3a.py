from datetime import timedelta

def date_to_calendar_week(date):
    return date.isocalendar()[1]

# Add n days to a date.
def add_days_to_date(date, n):
    return date + timedelta(days=n)