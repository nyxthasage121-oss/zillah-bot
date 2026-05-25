"""
Database connection and all query helpers.

All Discord IDs are stored as TEXT to avoid float precision loss.
"""

import os
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
    """Returns (auspex_role_id, mod_role_id, premonition_channel_id,
                uses_per_night, is_configured, night_length_days)"""
    return get_db().execute(
        "SELECT auspex_role_id, mod_role_id, premonition_channel_id, "
        "uses_per_night, is_configured, night_length_days "
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


def set_premonition_channel(guild_id: str, channel_id: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE server_config SET premonition_channel_id = ? WHERE guild_id = ?",
        (channel_id, guild_id),
    )
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


# ── vision_threads ────────────────────────────────────────────────────────────

def get_active_thread_motif(guild_id: str, user_id: str) -> str | None:
    row = get_db().execute(
        "SELECT motif FROM vision_threads "
        "WHERE guild_id = ? AND user_id = ? AND is_active = 1",
        (guild_id, user_id),
    ).fetchone()
    return row[0] if row else None
