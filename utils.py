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


def _anchor_and_length(
    night_length_days: int,
    sundown_time: str,
    sundown_timezone: str,
) -> tuple[float, datetime]:
    """
    Shared anchor computation used by get_night_start and get_elapsed_nights.

    Returns (night_seconds, anchor_utc) where anchor_utc is the first sundown
    moment at-or-after NIGHT_EPOCH in the configured timezone.
    """
    tz = resolve_timezone(sundown_timezone)

    try:
        hour, minute = (int(x) for x in sundown_time.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 20, 0  # safe default: 8 pm

    night_seconds = night_length_days * 24 * 3600

    epoch_local = NIGHT_EPOCH.astimezone(tz)
    anchor_local = epoch_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if anchor_local < epoch_local:
        anchor_local += timedelta(days=1)

    return night_seconds, anchor_local.astimezone(timezone.utc)


def get_night_start(
    night_length_days: int,
    sundown_time: str,
    sundown_timezone: str,
) -> datetime:
    """
    Return the UTC datetime when the current 'night' began.

    Nights are equal-length periods anchored to NIGHT_EPOCH.  Each night
    starts at sundown_time in sundown_timezone and lasts night_length_days.
    """
    night_seconds, anchor_utc = _anchor_and_length(
        night_length_days, sundown_time, sundown_timezone
    )
    now_utc = datetime.now(timezone.utc)
    elapsed = (now_utc - anchor_utc).total_seconds()

    if elapsed < 0:
        return anchor_utc  # shouldn't happen in production

    night_index = int(elapsed // night_seconds)
    return anchor_utc + timedelta(seconds=night_index * night_seconds)


def get_elapsed_nights(
    start_iso: str,
    night_length_days: int,
    sundown_time: str,
    sundown_timezone: str,
) -> int:
    """
    Return the number of complete night boundaries crossed since start_iso.

    Uses sundown-aligned night indices so a thread created mid-night counts
    as having started in night N, and the count only increments when the next
    sundown fires — not when N×24 hours have elapsed.
    """
    night_seconds, anchor_utc = _anchor_and_length(
        night_length_days, sundown_time, sundown_timezone
    )

    start_dt = datetime.fromisoformat(start_iso)
    now_utc = datetime.now(timezone.utc)

    start_elapsed = (start_dt - anchor_utc).total_seconds()
    start_night_idx = max(0, int(start_elapsed // night_seconds))

    now_elapsed = (now_utc - anchor_utc).total_seconds()
    current_night_idx = max(0, int(now_elapsed // night_seconds))

    return max(0, current_night_idx - start_night_idx)


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
