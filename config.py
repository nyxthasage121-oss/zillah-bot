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

VISION_TYPE_DESCRIPTIONS = """- Standard Vision: An atmospheric paragraph of sensory impressions with no clear meaning. Eerie, poetic, unsettling.
- Lucid Vision: A vivid, slightly more coherent vision that feels almost meaningful but remains ambiguous.
- Glitch Vision: A corrupted, fragmented vision. Use unusual formatting — incomplete sentences, repeated words, sudden cuts. Should feel broken.
- Echo Vision: A flash of emotional residue from a place or object. Impressionistic, tied to feeling rather than sight.
- Resonance Bleed: Written in second person present tense, as if the player is accidentally experiencing someone else's emotions right now.
- Nightmare Bleed: A vision that doesn't close cleanly. Write the vision, then add a short italicized postscript suggesting it has followed them into waking.
- The Witness: Written in first person from an unknown subject's point of view. The player sees through someone else's eyes briefly.
- The Warning: A vision with directional urgency. Vague but clearly important. End with a single sentence of quiet dread.
- Retrocognition Surge: Multiple fragmented timeline impressions simultaneously. Use formatting to suggest fragmentation — dashes, breaks, incomplete images."""

VISION_EMBED_COLOR = 0x8B0000
CLAUDE_MODEL = "claude-sonnet-4-20250514"
