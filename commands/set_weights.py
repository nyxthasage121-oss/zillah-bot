from typing import Literal

import discord
from discord import app_commands

import db
from config import VISION_EMBED_COLOR
from utils import has_mod_permission

VisionTypeChoice = Literal[
    "Standard Vision", "Lucid Vision", "Glitch Vision", "Echo Vision",
    "Resonance Bleed", "Nightmare Bleed", "The Witness", "The Warning",
    "Retrocognition Surge",
]


@app_commands.command(name="weights", description="Adjust vision type probability weights")
@app_commands.describe(
    vision_type="The vision type to adjust",
    weight="New weight (0 disables the type entirely, higher = more common)",
)
async def set_weights(
    interaction: discord.Interaction,
    vision_type: VisionTypeChoice,
    weight: app_commands.Range[int, 0, 200],
) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)

    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    if not has_mod_permission(interaction, str(config[1])):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    db.update_vision_weight(guild_id, vision_type, weight)

    # Show the updated full weights table.
    rows = db.get_vision_weights(guild_id)
    total = sum(w for _, w in rows)
    embed = discord.Embed(title="Vision Weights", color=VISION_EMBED_COLOR)
    lines = []
    for vt, w in sorted(rows, key=lambda x: -x[1]):
        pct = f"{w / total * 100:.1f}%" if total > 0 else "—"
        marker = " ✓" if vt == vision_type else ""
        lines.append(f"**{vt}**{marker} — {w} ({pct})")
    embed.description = "\n".join(lines)
    await interaction.response.send_message(embed=embed, ephemeral=True)
