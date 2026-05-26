import discord
from discord import app_commands

from config import VISION_EMBED_COLOR


@app_commands.command(name="help", description="Learn what Zillah does and how to use it")
async def zillah_help(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Zillah — The Sight of the Kindred",
        description=(
            "Zillah channels the Auspex discipline for Vampire: The Masquerade V5 "
            "play-by-post servers. If you carry the sight, the veil is thin."
        ),
        color=VISION_EMBED_COLOR,
    )

    embed.add_field(
        name="For players with Auspex",
        value=(
            "`/premonition` — Seek a vision. Works in the designated channel.\n"
            "`/myvisions` — Browse your full vision history.\n"
            "`/myjournal` — Two-tab journal: visions and recurring symbols side by side."
        ),
        inline=False,
    )

    embed.add_field(
        name="How nights work",
        value=(
            "Each night begins at sundown, configured by your Storyteller. "
            "You may seek visions a set number of times per night. "
            "When your sight is spent, Zillah will tell you exactly when it returns."
        ),
        inline=False,
    )

    embed.add_field(
        name="Vision types",
        value=(
            "Nine types of vision exist — Standard, Lucid, Glitch, Echo, Resonance Bleed, "
            "Nightmare Bleed, The Witness, The Warning, and Retrocognition Surge. "
            "Each carries a different quality of sight. Which you receive is not entirely in your hands."
        ),
        inline=False,
    )

    embed.add_field(
        name="Lucid Visions",
        value=(
            "Lucid Visions are interactive — you will be offered choices that shape what you see. "
            "Follow them through to the end; an abandoned vision is a vision half-lost."
        ),
        inline=False,
    )

    embed.add_field(
        name="Vision threads",
        value=(
            "Sometimes a motif — a recurring image or sensation — begins to weave itself into your visions. "
            "Threads may be assigned by your Storyteller or emerge on their own. "
            "Watch your journal. Patterns reveal themselves over time."
        ),
        inline=False,
    )

    embed.set_footer(text="For Storyteller commands, ask your Storyteller. · /settings shows server config.")
    await interaction.response.send_message(embed=embed, ephemeral=True)
