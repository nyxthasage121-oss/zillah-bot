"""
Utility helpers: timezone resolution, sundown-based night timing, clan flavor.
"""

import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import CLAN_FLAVOR, NIGHT_EPOCH, TIMEZONE_ALIASES


def resolve_timezone(tz_string: str) -> ZoneInfo:
    """
    Convert a timezone abbreviation or IANA name to a ZoneInfo object.

    Checks TIMEZONE_ALIASES first, then tries to construct ZoneInfo directly.
    Falls back to America/New_York for anything unrecognised.
    """
    normalized = tz_string.strip().upper()
    iana_name = TIMEZONE_ALIASES.get(normalized, tz_string.strip())
    try:
        return ZoneInfo(iana_name)
    except (ZoneInfoNotFoundError, KeyError):
        return ZoneInfo("America/New_York")


def get_night_start(
    night_length_days: int,
    sundown_time: str,
    sundown_timezone: str,
) -> datetime:
    """
    Return the UTC datetime when the current 'night' began.

    Nights are equal-length periods anchored to NIGHT_EPOCH.  Each night
    starts at sundown_time in sundown_timezone and lasts night_length_days.

    Algorithm
    ---------
    1. Convert NIGHT_EPOCH to local time in the configured timezone.
    2. Snap to the first sundown moment at-or-after that local epoch time
       (this becomes our reference anchor).
    3. Compute elapsed seconds from anchor → now (UTC).
    4. Floor-divide by night length to get the current night index.
    5. Return anchor + index × night_length as a UTC datetime.
    """
    tz = resolve_timezone(sundown_timezone)

    try:
        hour, minute = (int(x) for x in sundown_time.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 20, 0  # safe default: 8 pm

    night_seconds = night_length_days * 24 * 3600

    # First sundown at-or-after NIGHT_EPOCH, expressed in UTC
    epoch_local = NIGHT_EPOCH.astimezone(tz)
    anchor_local = epoch_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if anchor_local < epoch_local:
        anchor_local += timedelta(days=1)
    anchor_utc = anchor_local.astimezone(timezone.utc)

    now_utc = datetime.now(timezone.utc)
    elapsed = (now_utc - anchor_utc).total_seconds()

    if elapsed < 0:
        # Clock is somehow before the anchor (shouldn't happen in production)
        return anchor_utc

    night_index = int(elapsed // night_seconds)
    return anchor_utc + timedelta(seconds=night_index * night_seconds)


def get_clan_flavor(roles: list) -> str | None:
    """
    Check a list of discord.Role objects for a recognised Auspex clan name.

    Matching is a case-insensitive substring search on the role name so that
    role names like "Toreador Initiated" or "Clan: Malkavian" still match.
    Returns a random atmospheric flavor sentence, or None if no clan found.
    """
    for role in roles:
        role_lower = role.name.lower()
        for clan_key, sentences in CLAN_FLAVOR.items():
            if clan_key in role_lower:
                return random.choice(sentences)
    return None
