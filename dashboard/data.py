"""Data layer for the dashboard.

The kindred roster is still mocked — it needs Discord API user lookups +
character-sheet storage (not yet built). Drafts come from the real
vision_drafts table via db.py; everything else on the editor page (recent
visions, threads, symbols) is mocked until a future pass wires them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import db


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


def list_kindred(guild_id: str) -> list[Kindred]:
    return list(_MOCK_ROSTER)


def _real_drafts(guild_id: str, user_id: str) -> list[Draft]:
    """Pull this player's drafts out of the real vision_drafts table."""
    rows = db.list_drafts_for_player(guild_id, user_id)
    return [
        Draft(id=str(r["id"]), type=r["vision_type"], body=r["body"], when=r["updated_at"])
        for r in rows
    ]


def get_kindred(guild_id: str, user_id: str) -> KindredDetail | None:
    base = next((k for k in _MOCK_ROSTER if k.user_id == user_id), None)
    if not base:
        return None
    real_drafts = _real_drafts(guild_id, user_id)
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
    # generic detail for the other roster entries
    return KindredDetail(
        base=base,
        sire="unknown",
        embraced="—",
        sect="—",
        discipline_label=f"Auspex · {'●' * max(1, base.blood_potency)}",
        threads=[],
        symbols=[],
        recent_visions=[],
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
