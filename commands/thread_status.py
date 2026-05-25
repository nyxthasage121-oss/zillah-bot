from datetime import datetime, timezone

import discord
from discord import app_commands

import db
from config import VISION_EMBED_COLOR


def _has_mod_permission(interaction: discord.Interaction, mod_role_id: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return mod_role_id in [str(r.id) for r in interaction.user.roles]


@app_commands.command(name="thread_status", description="List all active vision threads for this server")
async def thread_status(interaction: discord.Interaction) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)

    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    if not _has_mod_permission(interaction, str(config[1])):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    threads = db.get_all_active_threads(guild_id)
    night_length_days = config[5] or 14
    now = datetime.now(timezone.utc)

    embed = discord.Embed(title="Active Vision Threads", color=VISION_EMBED_COLOR)

    if not threads:
        embed.description = "No active vision threads."
    else:
        lines = []
        for t in threads:
            try:
                member = interaction.guild.get_member(int(t["user_id"]))
                name = member.display_name if member else f"User {t['user_id']}"
            except Exception:
                name = f"User {t['user_id']}"

            start_dt = datetime.fromisoformat(t["start_timestamp"])
            elapsed_nights = (now - start_dt).total_seconds() / (night_length_days * 24 * 3600)
            remaining = max(0, t["duration_nights"] - int(elapsed_nights))
            source = "ST" if t["is_st_assigned"] else "Auto"

            lines.append(
                f"**{name}** · {source}\n"
                f"*{t['motif']}*\n"
                f"{remaining} night(s) remaining"
            )
        embed.description = "\n\n".join(lines)

    await interaction.response.send_message(embed=embed, ephemeral=True)
