"""
Static configuration: default weights, motifs, and vision prompt data.
All mutable server settings live in the database; these are read-only defaults
used only during /setup.
"""

DEFAULT_VISION_WEIGHTS: list[tuple[str, int]] = [
    ("Standard Vision",       40),
    ("Lucid Vision",          15),
    ("Glitch Vision",         15),
    ("Echo Vision",           10),
    ("Resonance Bleed",        7),
    ("Nightmare Bleed",        7),
    ("The Witness",            5),
    ("The Warning",            3),
    ("Retrocognition Surge",   3),
]

DEFAULT_MOTIFS: list[str] = [
    "a drowned woman with no face",
    "the smell of smoke with no source",
    "a broken clock frozen at the same hour",
    "the sound of bells that no one else hears",
    "a red door that appears in every vision",
    "a crow that watches but never moves",
    "handwriting that almost resembles your own",
    "the taste of blood that isn't yours",
    "a figure standing at the edge of every scene",
    "the feeling of being watched from below",
    "a child's laughter in empty rooms",
    "mirrors that show the wrong reflection",
]

VISION_TYPE_DESCRIPTIONS = """\
- Standard Vision: An atmospheric paragraph of sensory impressions with no clear meaning. Eerie, poetic, unsettling.
- Lucid Vision: A vivid, slightly more coherent vision that feels almost meaningful but remains ambiguous.
- Glitch Vision: A corrupted, fragmented vision using Discord markdown for visual corruption — see special formatting instructions below.
- Echo Vision: A flash of emotional residue from a place or object. Impressionistic, tied to feeling rather than sight.
- Resonance Bleed: Written in second person present tense, as if the player is accidentally experiencing someone else's emotions right now.
- Nightmare Bleed: A vision that doesn't close cleanly. Write the vision, then add a short italicized postscript suggesting it has followed them into waking.
- The Witness: Written in first person from an unknown subject's point of view. The player sees through someone else's eyes briefly.
- The Warning: A vision with directional urgency. Vague but clearly important. End with a single sentence of quiet dread.
- Retrocognition Surge: Multiple fragmented timeline impressions simultaneously. Use formatting to suggest fragmentation — dashes, breaks, incomplete images."""

GLITCH_VISION_INSTRUCTIONS = """\
GLITCH VISION — special Discord markdown formatting required:
You MUST mix ALL of the following aggressively to create visual corruption:
• ||hidden text|| for perceptions that flicker in and out of awareness
• ~~strikethrough~~ for impressions being erased or overwritten
• `code text` for clinical, intrusive, mechanical thought-fragments
• Zalgo-corrupted words using Unicode combining diacritics mid-word (e.g. ṫ̵̢̛h̸͕̩̐͆i̷͎͑s̸̗̿ c̷̙̏a̷̛͓ṅ̸͔n̷̩͝o̵͉͝t̷͓̚)
Sentences should be incomplete. Words may repeat repeat. Sudden cuts —"""

VISION_ALL_TYPES: list[str] = [
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

VISION_EMBED_COLOR = 0x8B0000   # Dark red — player visions
ST_EMBED_COLOR     = 0x4B0082   # Deep indigo — ST-sent visions
CLAUDE_MODEL       = "claude-sonnet-4-20250514"

# Vision Thread auto-trigger
AUTO_THREAD_CHANCE       = 0.08  # 8% chance per /premonition when no active thread
AUTO_THREAD_MIN_DURATION = 3     # nights
AUTO_THREAD_MAX_DURATION = 8     # nights

# Symbol detection
SYMBOL_DETECTION_COUNT = 15   # recent visions to scan
SYMBOL_MIN_VISIONS     = 3    # minimum visions needed before detection runs
