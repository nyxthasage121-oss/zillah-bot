"""
Database connection and all query helpers.

All Discord IDs are stored as TEXT to avoid float precision loss.
The _with_reconnect decorator gives every public function one automatic
retry with a fresh connection on any DB error (handles stale connections,
network blips, etc. without requiring a bot restart).
"""

import functools
import logging
import os
import random as _random
import libsql_experimental as libsql

from config import DEFAULT_VISION_WEIGHTS, DEFAULT_MOTIFS

logger = logging.getLogger("zillah.db")

_db: libsql.Connection | None = None


def _connect() -> libsql.Connection:
    return libsql.connect(
        database=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN"),
    )


def get_db() -> libsql.Connection:
    global _db
    if _db is None:
        _db = _connect()
    return _db


def _with_reconnect(fn):
    """On any DB error, drop the cached connection and retry once.
    If the second attempt also fails, the exception propagates normally."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        global _db
        try:
            return fn(*args, **kwargs)
        except Exception:
            _db = None  # force a fresh connection on next get_db()
            return fn(*args, **kwargs)
    return wrapper


def setup_database() -> None:
    """Create all tables. Called once at startup — not decorated (errors here are fatal)."""
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

    # Dashboard tables: STs compose visions in the web Codex; drafts persist
    # until inflicted, and an outbox decouples the web process from the bot
    # process for actually delivering visions to Discord.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_drafts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id        TEXT NOT NULL,
            player_user_id  TEXT NOT NULL,
            st_user_id      TEXT NOT NULL,
            vision_type     TEXT NOT NULL,
            body            TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_drafts_player ON vision_drafts(guild_id, player_user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_outbox (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id        TEXT NOT NULL,
            player_user_id  TEXT NOT NULL,
            st_user_id      TEXT NOT NULL,
            vision_type     TEXT NOT NULL,
            body            TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            created_at      TEXT NOT NULL,
            sent_at         TEXT,
            error           TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_pending ON vision_outbox(status, created_at)")

    conn.commit()
    logger.info("Database ready.")


# ── server_config ─────────────────────────────────────────────────────────────

@_with_reconnect
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


@_with_reconnect
def upsert_server_config(guild_id: str, auspex_role_id: str, mod_role_id: str) -> None:
    """Update roles without touching any other config (night length, sundown, etc.)."""
    conn = get_db()
    conn.execute(
        "INSERT INTO server_config (guild_id, auspex_role_id, mod_role_id, is_configured) "
        "VALUES (?, ?, ?, 1) "
        "ON CONFLICT (guild_id) DO UPDATE SET "
        "auspex_role_id = excluded.auspex_role_id, "
        "mod_role_id    = excluded.mod_role_id, "
        "is_configured  = 1",
        (guild_id, auspex_role_id, mod_role_id),
    )
    conn.commit()


@_with_reconnect
def init_server(guild_id: str) -> None:
    """Create a blank unconfigured row for a new server if one doesn't exist."""
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO server_config (guild_id) VALUES (?)", (guild_id,))
    conn.commit()


@_with_reconnect
def set_premonition_channel(guild_id: str, channel_id: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE server_config SET premonition_channel_id = ? WHERE guild_id = ?",
        (channel_id, guild_id),
    )
    conn.commit()


@_with_reconnect
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

@_with_reconnect
def reset_vision_weights(guild_id: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM vision_weights WHERE guild_id = ?", (guild_id,))
    for vision_type, weight in DEFAULT_VISION_WEIGHTS:
        conn.execute(
            "INSERT INTO vision_weights (guild_id, vision_type, weight) VALUES (?, ?, ?)",
            (guild_id, vision_type, weight),
        )
    conn.commit()


@_with_reconnect
def get_vision_weights(guild_id: str) -> list[tuple[str, int]]:
    return get_db().execute(
        "SELECT vision_type, weight FROM vision_weights WHERE guild_id = ?",
        (guild_id,),
    ).fetchall()


@_with_reconnect
def update_vision_weight(guild_id: str, vision_type: str, weight: int) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_weights SET weight = ? WHERE guild_id = ? AND vision_type = ?",
        (weight, guild_id, vision_type),
    )
    conn.commit()


# ── thread_pool ───────────────────────────────────────────────────────────────

@_with_reconnect
def get_thread_pool(guild_id: str) -> list[tuple[int, str]]:
    """Return all active motifs as (id, motif) pairs, oldest first."""
    rows = get_db().execute(
        "SELECT id, motif FROM thread_pool WHERE guild_id = ? AND is_active = 1 ORDER BY id",
        (guild_id,),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


@_with_reconnect
def remove_motif_from_pool(guild_id: str, motif_id: int) -> None:
    conn = get_db()
    conn.execute(
        "DELETE FROM thread_pool WHERE guild_id = ? AND id = ?",
        (guild_id, motif_id),
    )
    conn.commit()


@_with_reconnect
def reset_thread_pool(guild_id: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM thread_pool WHERE guild_id = ?", (guild_id,))
    for motif in DEFAULT_MOTIFS:
        conn.execute(
            "INSERT INTO thread_pool (guild_id, motif) VALUES (?, ?)",
            (guild_id, motif),
        )
    conn.commit()


@_with_reconnect
def add_motif_to_pool(guild_id: str, motif: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO thread_pool (guild_id, motif) VALUES (?, ?)",
        (guild_id, motif),
    )
    conn.commit()


@_with_reconnect
def get_random_motif(guild_id: str) -> str | None:
    rows = get_db().execute(
        "SELECT motif FROM thread_pool WHERE guild_id = ? AND is_active = 1",
        (guild_id,),
    ).fetchall()
    return _random.choice(rows)[0] if rows else None


# ── player_cooldowns ──────────────────────────────────────────────────────────

@_with_reconnect
def get_cooldown(guild_id: str, user_id: str) -> tuple | None:
    return get_db().execute(
        "SELECT uses_this_night, last_reset_timestamp FROM player_cooldowns "
        "WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()


@_with_reconnect
def reset_cooldown(guild_id: str, user_id: str, now_iso: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE player_cooldowns SET uses_this_night = 0, last_reset_timestamp = ? "
        "WHERE guild_id = ? AND user_id = ?",
        (now_iso, guild_id, user_id),
    )
    conn.commit()


@_with_reconnect
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
            "INSERT INTO player_cooldowns "
            "(guild_id, user_id, uses_this_night, last_reset_timestamp) "
            "VALUES (?, ?, 1, ?)",
            (guild_id, user_id, now_iso),
        )
    conn.commit()


# ── vision_history ────────────────────────────────────────────────────────────

@_with_reconnect
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


@_with_reconnect
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


@_with_reconnect
def count_vision_history(guild_id: str, user_id: str) -> int:
    row = get_db().execute(
        "SELECT COUNT(*) FROM vision_history WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()
    return row[0] if row else 0


@_with_reconnect
def get_recent_visions_text(guild_id: str, user_id: str, limit: int) -> list[str]:
    rows = get_db().execute(
        "SELECT vision_text FROM vision_history WHERE guild_id = ? AND user_id = ? "
        "ORDER BY timestamp DESC LIMIT ?",
        (guild_id, user_id, limit),
    ).fetchall()
    return [r[0] for r in rows]


# ── vision_threads ────────────────────────────────────────────────────────────

@_with_reconnect
def get_active_thread(guild_id: str, user_id: str) -> dict | None:
    """Return the active thread row as a dict, or None."""
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


@_with_reconnect
def deactivate_thread(guild_id: str, user_id: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_threads SET is_active = 0 "
        "WHERE guild_id = ? AND user_id = ? AND is_active = 1",
        (guild_id, user_id),
    )
    conn.commit()


@_with_reconnect
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


@_with_reconnect
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

@_with_reconnect
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


@_with_reconnect
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


@_with_reconnect
def clear_detected_symbols(guild_id: str, user_id: str) -> None:
    """Remove all detected symbols for a player."""
    conn = get_db()
    conn.execute(
        "DELETE FROM detected_symbols WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    conn.commit()


# ── vision_drafts ─────────────────────────────────────────────────────────────

@_with_reconnect
def create_draft(
    guild_id: str,
    player_user_id: str,
    st_user_id: str,
    vision_type: str,
    body: str,
    now_iso: str,
) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO vision_drafts "
        "(guild_id, player_user_id, st_user_id, vision_type, body, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, player_user_id, st_user_id, vision_type, body, now_iso, now_iso),
    )
    conn.commit()
    return cur.lastrowid


@_with_reconnect
def update_draft(draft_id: int, vision_type: str, body: str, now_iso: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_drafts SET vision_type = ?, body = ?, updated_at = ? WHERE id = ?",
        (vision_type, body, now_iso, draft_id),
    )
    conn.commit()


@_with_reconnect
def delete_draft(draft_id: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM vision_drafts WHERE id = ?", (draft_id,))
    conn.commit()


@_with_reconnect
def list_drafts_for_player(guild_id: str, player_user_id: str) -> list[dict]:
    rows = get_db().execute(
        "SELECT id, vision_type, body, updated_at FROM vision_drafts "
        "WHERE guild_id = ? AND player_user_id = ? ORDER BY updated_at DESC",
        (guild_id, player_user_id),
    ).fetchall()
    return [{"id": r[0], "vision_type": r[1], "body": r[2], "updated_at": r[3]} for r in rows]


@_with_reconnect
def get_draft(draft_id: int) -> dict | None:
    r = get_db().execute(
        "SELECT id, guild_id, player_user_id, st_user_id, vision_type, body, updated_at "
        "FROM vision_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()
    if not r:
        return None
    return {
        "id": r[0], "guild_id": r[1], "player_user_id": r[2], "st_user_id": r[3],
        "vision_type": r[4], "body": r[5], "updated_at": r[6],
    }


# ── aggregations for the dashboard ──────────────────────────────────────────

@_with_reconnect
def get_roster_aggregates(guild_id: str, user_ids: list[str]) -> dict[str, dict]:
    """For each user_id in the list, return aggregate stats:
        { last_vision_type, last_vision_when, threads_count, drafts_count }
    Users with no activity are absent from the returned dict.
    """
    if not user_ids:
        return {}

    placeholders = ",".join("?" * len(user_ids))
    out: dict[str, dict] = {}

    # Last vision per user: filter to the max-id row per (guild, user).
    for row in get_db().execute(
        f"SELECT user_id, vision_type, timestamp FROM vision_history "
        f"WHERE guild_id = ? AND user_id IN ({placeholders}) "
        f"AND id IN (SELECT MAX(id) FROM vision_history WHERE guild_id = ? "
        f"AND user_id IN ({placeholders}) GROUP BY user_id)",
        [guild_id, *user_ids, guild_id, *user_ids],
    ).fetchall():
        out.setdefault(row[0], {})
        out[row[0]]["last_vision_type"] = row[1]
        out[row[0]]["last_vision_when"] = row[2]

    for row in get_db().execute(
        f"SELECT user_id, COUNT(*) FROM vision_threads "
        f"WHERE guild_id = ? AND user_id IN ({placeholders}) AND is_active = 1 "
        f"GROUP BY user_id",
        [guild_id, *user_ids],
    ).fetchall():
        out.setdefault(row[0], {})["threads_count"] = row[1]

    for row in get_db().execute(
        f"SELECT player_user_id, COUNT(*) FROM vision_drafts "
        f"WHERE guild_id = ? AND player_user_id IN ({placeholders}) "
        f"GROUP BY player_user_id",
        [guild_id, *user_ids],
    ).fetchall():
        out.setdefault(row[0], {})["drafts_count"] = row[1]

    return out


# ── vision_outbox ─────────────────────────────────────────────────────────────

@_with_reconnect
def enqueue_inflict(
    guild_id: str,
    player_user_id: str,
    st_user_id: str,
    vision_type: str,
    body: str,
    now_iso: str,
) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO vision_outbox "
        "(guild_id, player_user_id, st_user_id, vision_type, body, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, player_user_id, st_user_id, vision_type, body, now_iso),
    )
    conn.commit()
    return cur.lastrowid


@_with_reconnect
def drain_outbox_pending(limit: int = 10) -> list[dict]:
    """Return pending outbox rows oldest-first, up to `limit`."""
    rows = get_db().execute(
        "SELECT id, guild_id, player_user_id, st_user_id, vision_type, body "
        "FROM vision_outbox WHERE status = 'pending' ORDER BY created_at LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {"id": r[0], "guild_id": r[1], "player_user_id": r[2], "st_user_id": r[3],
         "vision_type": r[4], "body": r[5]}
        for r in rows
    ]


@_with_reconnect
def mark_outbox_sent(outbox_id: int, now_iso: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_outbox SET status = 'sent', sent_at = ? WHERE id = ?",
        (now_iso, outbox_id),
    )
    conn.commit()


@_with_reconnect
def mark_outbox_failed(outbox_id: int, error: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE vision_outbox SET status = 'failed', error = ? WHERE id = ?",
        (error, outbox_id),
    )
    conn.commit()
