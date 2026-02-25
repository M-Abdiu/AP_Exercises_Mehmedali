"""
Timezone time converter module
Converts a local date+time in a source IANA timezone to an aware datetime in a target IANA timezone.
Explicit DST policy: caller must provide fold (0/1) and nonexistent policy ('raise' or 'shift_forward').
"""

from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "convert_time",
    "local_to_utc",
    "get_zoneinfo",
]

_UTC_ZONE = ZoneInfo("UTC")

class TimezoneConversionError(Exception):
    pass

def get_zoneinfo(tz_id: str) -> ZoneInfo:
    """Return ZoneInfo for tz_id, raise TimezoneConversionError if not found."""
    try:
        return ZoneInfo(tz_id)
    except ZoneInfoNotFoundError:
        raise TimezoneConversionError(f"Timezone '{tz_id}' not found or tzdata missing.")


def local_to_utc(local_dt: datetime, source_tz: str, *, fold: int, nonexistent: str) -> datetime:
    """
    Convert a local wall-time datetime in source_tz to UTC aware datetime.

    local_dt must be a naive datetime (tzinfo is None) representing the intended local clock time.
    fold: 0 or 1 (for ambiguous times)
    nonexistent: 'raise' or 'shift_forward' (for nonexistent times)
    """
    if local_dt.tzinfo is not None:
        raise ValueError("local_dt must be naive (tzinfo is None)")
    if fold not in (0, 1):
        raise ValueError("fold must be 0 or 1")
    if nonexistent not in ("raise", "shift_forward"):
        raise ValueError("nonexistent must be 'raise' or 'shift_forward'")
    tz = get_zoneinfo(source_tz)
    # Attach tz and fold
    aware_local = local_dt.replace(tzinfo=tz, fold=fold)
    # Round-trip: check if this local time exists
    try:
        utc_dt = aware_local.astimezone(_UTC_ZONE)
    except Exception as e:
        raise TimezoneConversionError(f"Failed to convert to UTC: {e}")
    # Check if round-trip returns same local time
    roundtrip = utc_dt.astimezone(tz)
    if (roundtrip.replace(tzinfo=None) != local_dt) or (roundtrip.fold != fold):
        # Nonexistent time
        if nonexistent == "raise":
            raise TimezoneConversionError(f"Local time {local_dt} in {source_tz} is nonexistent due to DST transition.")
        elif nonexistent == "shift_forward":
            # Shift forward by 1 hour (typical DST gap)
            shifted = local_dt + timedelta(hours=1)
            aware_shifted = shifted.replace(tzinfo=tz, fold=fold)
            utc_dt = aware_shifted.astimezone(_UTC_ZONE)
            return utc_dt
    return utc_dt


def convert_time(date_str: str, time_str: str, source_tz: str, target_tz: str, *, fold: int, nonexistent: str) -> datetime:
    """
    Convert local date+time in source_tz to aware datetime in target_tz.
    fold: 0 or 1 (for ambiguous times)
    nonexistent: 'raise' or 'shift_forward' (for nonexistent times)
    """
    d = date.fromisoformat(date_str)
    t = time.fromisoformat(time_str)
    local_dt = datetime.combine(d, t)
    utc_dt = local_to_utc(local_dt, source_tz, fold=fold, nonexistent=nonexistent)
    target_zone = get_zoneinfo(target_tz)
    return utc_dt.astimezone(target_zone)
