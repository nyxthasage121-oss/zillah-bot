"""
Database connection and all query helpers.

All Discord IDs are stored as TEXT to avoid float precision loss.
"""

import os
import random as _random
import libsql_experimental as libsql

from config import DEFAULT_VISION_WEIGHTS, DEFAULT_MOTIFS


def get_db() -> libsql.Connection:
    return libsql.connect(
        database=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN"),
    )


def setup_database() -> None:
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id                TEXT PRIMARY KEY,
            auspex_role_id          TEXT,
            mod_role_id             TEXT,
            premonition_channel_id  TEXT,
            night_length_days       INTEGER DEFAULT 14,
            sundown_time            TEXT    DEFAULT '20:00',
            sundown_timezone        TEXT    DEFAULT 'EST',
            uses_per_night          INTEGER DEFAULT 1,
            is_configured           INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_weights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    TEXT,
            vision_type TEXT,
            weight      INTEGER DEFAULT 10
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_cooldowns (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id             TEXT,
            user_id              TEXT,
            uses_this_night      INTEGER DEFAULT 0,
            last_reset_timestamp TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id        TEXT,
            user_id         TEXT,
            vision_type     TEXT,
            vision_text     TEXT,
            timestamp       TEXT,
            is_st_triggered INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_threads (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id        TEXT,
            user_id         TEXT,
            motif           TEXT,
            start_timestamp TEXT,
            duration_nights INTEGER,
            is_active       INTEGER DEFAULT 1,
            is_st_assigned  INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS detected_symbols (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id         TEXT,
            user_id          TEXT,
            symbol           TEXT,
            first_seen       TEXT,
            last_seen        TEXT,
            occurrence_count INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS thread_pool (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id  TEXT,
            motif     TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    print("Database ready.")


# ── server_config ─────────────────────────────────────────────────────────────

def get_server_config(guild_id: str) -> tuple | None:
    """Returns (auspex_role_id[0], mod_role_id[1], premonition_channel_id[2],
                uses_per_night[3], is_configured[4], night_length_days[5],
                sundown_time[6], sundown_timezone[7])"""
    return get_db().execute(
        "SELECT auspex_role_id, mod_role_id, premonition_channel_id, "
        "uses_per_night, is_configured, night_length_days, "
        "sundown_time, sundown_timezone "
        "FROM server_config WHERE guild_id = ?",
        (guild_id,),
    ).fetchone()


def upsert_server_config(guild_id: str, auspex_role_id: str, mod_role_id: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO server_config "
        "(guild_id, auspex_role_id, mod_role_id, is_configured) VALUES (?, ?, ?, 1)",
        (guild_id, auspex_role_id, mod_role_id),
    )
    conn.commit()


def init_server(guild_id: str) -> None:
    """Creates a blank unconfigured row for a new server if one doesn't already exist."""
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO server_config (guild_id) VALUES (?)", (guild_id,))
    conn.commit()


def set_premonition_channel(guild_id: str, channel_id: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE server_config SET premonition_channel_id = ? WHERE guild_id = ?",
        (channel_id, guild_id),
    )
    conn.commit()


def update_cooldown_config(
    guild_id: str,
    night_length_days: int | None = None,
    uses_per_night: int | None = None,
    sundown_time: str | None = None,
    sundown_timezone: str | None = None,
) -> None:
    """Update whichever cooldown config fields are provided (None = leave unchanged)."""
    updates, values = [], []
    if night_length_days is not None:
        updates.append("night_length_days = ?")
        values.append(night_length_days)
    if uses_per_night is not None:
        updates.append("uses_per_night = ?")
        values.append(uses_per_night)
    if sundown_time is not None:
        updates.append("sundown_time = ?")
        values.append(sundown_time)
    if sundown_timezone is not None:
        updates.append("sundown_timezone = ?")
        values.append(sundown_timezone)
    if not updates:
        return
    values.append(guild_id)
    conn = get_db()
    conn.execute(f"UPDATE server_config SET {', '.join(updates)} WHERE guild_id = ?", values)
    conn.commit()


# ── vision_weights ────────────────────────────────────────────────────────────

def reset_vision_weights(guild_id: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM vision_weights WHERE guild_id = ?", (guild_id,))
    for vision_type, weight in DEFAULT_VISION_WEIGHTS:
        conn.execute(
            "INSERT INTO vision_weights (guild_id, vision_type, weight) VALUES (?, ?, ?)",
            (guild_id, vision_type, weight),
        )
    conn.commit()


def get_vision_weights(guild_id: str) -> list[tuple[str, int]]:
    return get_db().execute(
        "SELECT vision_type, weight FROM vision_weights WHERE guild_id = ?",
        (guild_id,),
    ).fetchall()


def update_vision_weight(guild_id: str, vision_type: str, weight: int) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_weights SET weight = ? WHERE guild_id = ? AND vision_type = ?",
        (weight, guild_id, vision_type),
    )
    conn.commit()


# ── thread_pool ───────────────────────────────────────────────────────────────

def reset_thread_pool(guild_id: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM thread_pool WHERE guild_id = ?", (guild_id,))
    for motif in DEFAULT_MOTIFS:
        conn.execute(
            "INSERT INTO thread_pool (guild_id, motif) VALUES (?, ?)",
            (guild_id, motif),
        )
    conn.commit()


def add_motif_to_pool(guild_id: str, motif: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO thread_pool (guild_id, motif) VALUES (?, ?)",
        (guild_id, motif),
    )
    conn.commit()


def get_random_motif(guild_id: str) -> str | None:
    rows = get_db().execute(
        "SELECT motif FROM thread_pool WHERE guild_id = ? AND is_active = 1",
        (guild_id,),
    ).fetchall()
    return _random.choice(rows)[0] if rows else None


# ── player_cooldowns ──────────────────────────────────────────────────────────

def get_cooldown(guild_id: str, user_id: str) -> tuple | None:
    return get_db().execute(
        "SELECT uses_this_night, last_reset_timestamp FROM player_cooldowns "
        "WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()


def reset_cooldown(guild_id: str, user_id: str, now_iso: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE player_cooldowns SET uses_this_night = 0, last_reset_timestamp = ? "
        "WHERE guild_id = ? AND user_id = ?",
        (now_iso, guild_id, user_id),
    )
    conn.commit()


def increment_cooldown(guild_id: str, user_id: str, now_iso: str, exists: bool) -> None:
    conn = get_db()
    if exists:
        conn.execute(
            "UPDATE player_cooldowns SET uses_this_night = uses_this_night + 1 "
            "WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO player_cooldowns (guild_id, user_id, uses_this_night, last_reset_timestamp) "
            "VALUES (?, ?, 1, ?)",
            (guild_id, user_id, now_iso),
        )
    conn.commit()


# ── vision_history ────────────────────────────────────────────────────────────

def save_vision(
    guild_id: str,
    user_id: str,
    vision_type: str,
    vision_text: str,
    timestamp_iso: str,
    is_st_triggered: bool = False,
) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO vision_history "
        "(guild_id, user_id, vision_type, vision_text, timestamp, is_st_triggered) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, vision_type, vision_text, timestamp_iso, int(is_st_triggered)),
    )
    conn.commit()


def get_vision_history_page(
    guild_id: str, user_id: str, page: int, per_page: int
) -> list[dict]:
    offset = page * per_page
    rows = get_db().execute(
        "SELECT vision_type, vision_text, timestamp, is_st_triggered "
        "FROM vision_history WHERE guild_id = ? AND user_id = ? "
        "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (guild_id, user_id, per_page, offset),
    ).fetchall()
    return [
        {
            "vision_type": r[0],
            "vision_text": r[1],
            "timestamp": r[2],
            "is_st_triggered": bool(r[3]),
        }
        for r in rows
    ]


def count_vision_history(guild_id: str, user_id: str) -> int:
    row = get_db().execute(
        "SELECT COUNT(*) FROM vision_history WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()
    return row[0] if row else 0


def get_recent_visions_text(guild_id: str, user_id: str, limit: int) -> list[str]:
    rows = get_db().execute(
        "SELECT vision_text FROM vision_history WHERE guild_id = ? AND user_id = ? "
        "ORDER BY timestamp DESC LIMIT ?",
        (guild_id, user_id, limit),
    ).fetchall()
    return [r[0] for r in rows]


# ── vision_threads ────────────────────────────────────────────────────────────

def get_active_thread(guild_id: str, user_id: str) -> dict | None:
    """Returns the full active thread row as a dict, or None."""
    row = get_db().execute(
        "SELECT id, motif, start_timestamp, duration_nights, is_st_assigned "
        "FROM vision_threads WHERE guild_id = ? AND user_id = ? AND is_active = 1",
        (guild_id, user_id),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "motif": row[1],
        "start_timestamp": row[2],
        "duration_nights": row[3],
        "is_st_assigned": bool(row[4]),
    }


def deactivate_thread(guild_id: str, user_id: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_threads SET is_active = 0 "
        "WHERE guild_id = ? AND user_id = ? AND is_active = 1",
        (guild_id, user_id),
    )
    conn.commit()


def create_thread(
    guild_id: str,
    user_id: str,
    motif: str,
    duration_nights: int,
    is_st_assigned: bool,
    now_iso: str,
) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO vision_threads "
        "(guild_id, user_id, motif, start_timestamp, duration_nights, is_active, is_st_assigned) "
        "VALUES (?, ?, ?, ?, ?, 1, ?)",
        (guild_id, user_id, motif, now_iso, duration_nights, int(is_st_assigned)),
    )
    conn.commit()


def get_all_active_threads(guild_id: str) -> list[dict]:
    rows = get_db().execute(
        "SELECT id, user_id, motif, start_timestamp, duration_nights, is_st_assigned "
        "FROM vision_threads WHERE guild_id = ? AND is_active = 1",
        (guild_id,),
    ).fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "motif": r[2],
            "start_timestamp": r[3],
            "duration_nights": r[4],
            "is_st_assigned": bool(r[5]),
        }
        for r in rows
    ]


# ── detected_symbols ──────────────────────────────────────────────────────────

def upsert_detected_symbol(guild_id: str, user_id: str, symbol: str, now_iso: str) -> None:
    conn = get_db()
    existing = conn.execute(
        "SELECT id, occurrence_count FROM detected_symbols "
        "WHERE guild_id = ? AND user_id = ? AND symbol = ?",
        (guild_id, user_id, symbol),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE detected_symbols SET last_seen = ?, occurrence_count = ? WHERE id = ?",
            (now_iso, existing[1] + 1, existing[0]),
        )
    else:
        conn.execute(
            "INSERT INTO detected_symbols "
            "(guild_id, user_id, symbol, first_seen, last_seen, occurrence_count) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (guild_id, user_id, symbol, now_iso, now_iso),
        )
    conn.commit()


def get_detected_symbols(guild_id: str, user_id: str) -> list[dict]:
    rows = get_db().execute(
        "SELECT symbol, first_seen, last_seen, occurrence_count "
        "FROM detected_symbols WHERE guild_id = ? AND user_id = ? "
        "ORDER BY occurrence_count DESC, last_seen DESC",
        (guild_id, user_id),
    ).fetchall()
    return [
        {
            "symbol": r[0],
            "first_seen": r[1],
            "last_seen": r[2],
            "occurrence_count": r[3],
        }
        for r in rows
    ]
