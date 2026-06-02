"""Data layer for the dashboard.

The kindred roster is real: Discord guild members with the Auspex role,
augmented with last-vision / threads / drafts counts from the DB.

Character-sheet fields (clan from role-name substring match;
hunger/humanity/blood_potency/sire/embraced/sect/discipline_label) don't
exist in storage yet — those are returned as zeros / "—" until a future
pass adds a character_sheets table.

Drafts come from the real vision_drafts table via db.py.

In dev mode (DASHBOARD_DEV_PREVIEW=1, guild_id == "100") the mock roster
is returned instead so the templates can be reviewed without Discord
API access.
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field

import db
from config import CLAN_FLAVOR
from dashboard import discord_api


@dataclass
class Kindred:
    user_id: str
    name: str
    epithet: str
    clan: str            # lowercase: toreador, tremere, malkavian, salubri, hecata, banuhaqim
    generation: int
    hunger: int          # 0..5
    humanity: int        # 0..10
    blood_potency: int   # 0..10
    last_vision_type: str
    last_vision_when: str
    threads_count: int
    drafts_count: int


@dataclass
class Vision:
    type: str
    when: str
    body: str


@dataclass
class Thread:
    title: str
    when_opened: str
    visions_count: int
    is_primary: bool = False


@dataclass
class Symbol:
    name: str
    count: int


@dataclass
class Draft:
    id: str       # str so the same shape works for both DB ints and mock string ids
    type: str
    body: str
    when: str


@dataclass
class KindredDetail:
    base: Kindred
    sire: str
    embraced: str
    sect: str
    discipline_label: str
    threads: list[Thread] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    recent_visions: list[Vision] = field(default_factory=list)
    drafts: list[Draft] = field(default_factory=list)


# --- mock chronicle ---

_MOCK_ROSTER: list[Kindred] = [
    Kindred("100000000000000001", "Lucien Marchetti",   "The Rose of the Ponte Vecchio",
            "toreador", 8, hunger=3, humanity=6, blood_potency=3,
            last_vision_type="Resonance Bleed", last_vision_when="2 nights past",
            threads_count=2, drafts_count=3),
    Kindred("100000000000000002", "Yseult Vasquez",     "Regent of Chapter House Castile",
            "tremere",  9, hunger=1, humanity=5, blood_potency=4,
            last_vision_type="The Warning", last_vision_when="6 nights past",
            threads_count=1, drafts_count=1),
    Kindred("100000000000000003", "Cassiel",            "no surname remembered · the Cobwalker",
            "malkavian", 7, hunger=4, humanity=3, blood_potency=5,
            last_vision_type="Nightmare Bleed", last_vision_when="last night",
            threads_count=4, drafts_count=0),
    Kindred("100000000000000004", "Aurelio Cortés",     "Master of the Belmont Theatre",
            "toreador", 11, hunger=2, humanity=7, blood_potency=2,
            last_vision_type="Echo Vision", last_vision_when="4 nights past",
            threads_count=1, drafts_count=2),
    Kindred("100000000000000005", "Sister Magdalene",   "of the Giovanni faction · keeps the Old Cemetery",
            "hecata",   10, hunger=0, humanity=6, blood_potency=3,
            last_vision_type="Retrocognition", last_vision_when="11 nights past",
            threads_count=0, drafts_count=0),
    Kindred("100000000000000006", "Idris al-Najjar",    "Judge of the Anarch Council",
            "banuhaqim", 8, hunger=3, humanity=7, blood_potency=3,
            last_vision_type="The Witness", last_vision_when="9 nights past",
            threads_count=1, drafts_count=0),
]


# ── Roster cache ───────────────────────────────────────────────────────────
#
# Discord guild membership doesn't change often. The bot also pays a real
# rate-limit cost when we list members. Cache the raw computed roster
# per-guild for ROSTER_TTL seconds.

ROSTER_TTL = 300  # 5 minutes
_roster_cache: dict[str, tuple[float, list[Kindred]]] = {}


def _is_dev_mock_guild(guild_id: str) -> bool:
    return os.getenv("DASHBOARD_DEV_PREVIEW") == "1" and str(guild_id) == "100"


def _clan_from_role_names(role_names: list[str]) -> str | None:
    """Mirror utils.get_clan_flavor's substring match — return the lowercase
    clan key (toreador / tremere / …) or None."""
    for rn in role_names:
        rn_lower = rn.lower()
        for clan_key in CLAN_FLAVOR.keys():
            if clan_key in rn_lower:
                return clan_key
    return None


async def list_kindred(guild_id: str) -> list[Kindred]:
    """Return the roster for a guild — Discord guild members holding the
    Auspex role, augmented with DB-derived activity."""
    if _is_dev_mock_guild(guild_id):
        return list(_MOCK_ROSTER)

    cached = _roster_cache.get(guild_id)
    if cached and time.time() - cached[0] < ROSTER_TTL:
        return cached[1]

    config = await asyncio.to_thread(db.get_server_config, guild_id)
    if not config or config[4] == 0:
        return []
    auspex_role_id = str(config[0]) if config[0] else None
    if not auspex_role_id:
        return []

    roles, members = await asyncio.gather(
        discord_api.fetch_guild_roles(guild_id),
        discord_api.fetch_guild_members(guild_id),
    )
    role_name_by_id: dict[str, str] = {str(r["id"]): r["name"] for r in roles}

    auspex_members = [
        m for m in members if auspex_role_id in [str(rid) for rid in m.get("roles", [])]
    ]
    user_ids = [str(m["user"]["id"]) for m in auspex_members]
    agg = await asyncio.to_thread(db.get_roster_aggregates, guild_id, user_ids)

    roster: list[Kindred] = []
    for m in auspex_members:
        u = m["user"]
        uid = str(u["id"])
        member_role_names = [role_name_by_id.get(str(rid), "") for rid in m.get("roles", [])]
        clan = _clan_from_role_names(member_role_names) or "toreador"  # default if no clan role
        a = agg.get(uid, {})
        roster.append(Kindred(
            user_id=uid,
            name=m.get("nick") or u.get("global_name") or u.get("username") or uid,
            epithet="",
            clan=clan,
            generation=0,
            hunger=0,
            humanity=0,
            blood_potency=0,
            last_vision_type=a.get("last_vision_type", "—"),
            last_vision_when=a.get("last_vision_when", "—"),
            threads_count=a.get("threads_count", 0),
            drafts_count=a.get("drafts_count", 0),
        ))

    # Sort by recent activity — players with recent visions first, then by name.
    roster.sort(key=lambda k: (k.last_vision_when == "—", -len(k.last_vision_when), k.name.lower()))

    _roster_cache[guild_id] = (time.time(), roster)
    return roster


def _real_drafts(guild_id: str, user_id: str) -> list[Draft]:
    """Pull this player's drafts out of the real vision_drafts table."""
    rows = db.list_drafts_for_player(guild_id, user_id)
    return [
        Draft(id=str(r["id"]), type=r["vision_type"], body=r["body"], when=r["updated_at"])
        for r in rows
    ]


async def get_kindred(guild_id: str, user_id: str) -> KindredDetail | None:
    real_drafts = _real_drafts(guild_id, user_id)

    if _is_dev_mock_guild(guild_id):
        base = next((k for k in _MOCK_ROSTER if k.user_id == user_id), None)
        if not base:
            return None
        if user_id == "100000000000000001":
            return KindredDetail(
                base=base,
                sire="Vittoria della Rovere",
                embraced="anno 1894",
                sect="Camarilla",
                discipline_label="Auspex · ●●●● · Scry the Soul unlocked",
                threads=[
                    Thread("The Mirror's Reflection", "9 nights past", 4, is_primary=True),
                    Thread("Whispers in the Velvet",  "3 nights past", 2),
                ],
                symbols=[
                    Symbol("broken glass", 7),
                    Symbol("red moths", 5),
                    Symbol("the woman in white", 4),
                    Symbol("a closed door", 3),
                    Symbol("candlewax", 3),
                    Symbol("violin string", 2),
                ],
                recent_visions=[
                    Vision("Resonance Bleed", "2 nights past",
                           "Velvet curtains stir though no window is open. From beneath them seeps the scent of jasmine and copper, and a sound like a violin string drawn slowly across bone…"),
                    Vision("Standard Vision", "5 nights past",
                           "A hand you do not recognise sets a single red moth upon the rim of your glass. It does not burn though the candle is close. It watches."),
                    Vision("The Warning", "8 nights past",
                           "Do not return to the gallery on Calle Aviles. The painting you admire there has begun, lately, to admire you back."),
                ],
                drafts=real_drafts,
            )
        return KindredDetail(
            base=base, sire="unknown", embraced="—", sect="—",
            discipline_label=f"Auspex · {'●' * max(1, base.blood_potency)}",
            threads=[], symbols=[], recent_visions=[], drafts=real_drafts,
        )

    # Real path: find the member in the cached roster, then load DB-derived
    # detail (threads, symbols, recent visions).
    roster = await list_kindred(guild_id)
    base = next((k for k in roster if k.user_id == user_id), None)
    if not base:
        return None

    threads_rows = await asyncio.to_thread(db.get_active_thread, guild_id, user_id)
    threads = []
    if threads_rows:
        threads.append(Thread(
            title=threads_rows["motif"],
            when_opened=threads_rows["start_timestamp"][:10],
            visions_count=0,
            is_primary=True,
        ))

    symbol_rows = await asyncio.to_thread(db.get_detected_symbols, guild_id, user_id)
    symbols = [Symbol(name=s["symbol"], count=s["occurrence_count"]) for s in symbol_rows]

    recent_rows = await asyncio.to_thread(db.get_recent_visions_text, guild_id, user_id, 3)
    recent = [Vision(type="Recent", when="", body=t) for t in recent_rows]

    return KindredDetail(
        base=base,
        sire="—",
        embraced="—",
        sect="—",
        discipline_label="Auspex",
        threads=threads,
        symbols=symbols,
        recent_visions=recent,
        drafts=real_drafts,
    )


# nine vision types, in display order
VISION_TYPES: list[str] = [
    "Standard Vision",
    "Lucid Vision",
    "Glitch Vision",
    "Echo Vision",
    "Resonance Bleed",
    "Nightmare Bleed",
    "The Witness",
    "The Warning",
    "Retrocognition Surge",
]

# clans -> display label
CLAN_LABELS: dict[str, str] = {
    "toreador":  "Toreador",
    "tremere":   "Tremere",
    "malkavian": "Malkavian",
    "salubri":   "Salubri",
    "hecata":    "Hecata",
    "banuhaqim": "Banu Haqim",
}
