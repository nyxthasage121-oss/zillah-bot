import discord
from discord import app_commands

import db
from config import VISION_EMBED_COLOR
from utils import has_mod_permission


@app_commands.command(
    name="resetweights",
    description="Reset all vision type weights back to their defaults",
)
async def reset_weights(interaction: discord.Interaction) -> None:
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

    db.reset_vision_weights(guild_id)

    rows = db.get_vision_weights(guild_id)
    total = sum(w for _, w in rows)
    embed = discord.Embed(title="Vision Weights — Reset to Defaults", color=VISION_EMBED_COLOR)
    lines = [
        f"**{vt}** — {w} ({w / total * 100:.1f}%)" if total else f"**{vt}** — {w}"
        for vt, w in sorted(rows, key=lambda x: -x[1])
    ]
    embed.description = "\n".join(lines)
    await interaction.response.send_message(embed=embed, ephemeral=True)
