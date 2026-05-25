import discord
from discord import app_commands

import db
from config import VISION_EMBED_COLOR
from utils import get_elapsed_nights, has_mod_permission


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

    if not has_mod_permission(interaction, str(config[1])):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    night_length_days = config[5] or 14
    sundown_time      = config[6] or "20:00"
    sundown_timezone  = config[7] or "EST"

    threads = db.get_all_active_threads(guild_id)
    embed = discord.Embed(title="Active Vision Threads", color=VISION_EMBED_COLOR)

    lines = []
    for t in threads:
        elapsed = get_elapsed_nights(
            t["start_timestamp"], night_length_days, sundown_time, sundown_timezone
        )
        # Auto-deactivate threads that have run their course.
        if elapsed >= t["duration_nights"]:
            db.deactivate_thread(guild_id, t["user_id"])
            continue

        try:
            member = interaction.guild.get_member(int(t["user_id"]))
            name = member.display_name if member else f"User {t['user_id']}"
        except Exception:
            name = f"User {t['user_id']}"

        remaining = t["duration_nights"] - elapsed
        source = "ST" if t["is_st_assigned"] else "Auto"
        lines.append(
            f"**{name}** · {source}\n"
            f"*{t['motif']}*\n"
            f"{remaining} night(s) remaining"
        )

    embed.description = "\n\n".join(lines) if lines else "No active vision threads."
    await interaction.response.send_message(embed=embed, ephemeral=True)
