from datetime import datetime, timezone

import discord
from discord import app_commands

import db
from views import ConfirmOverwriteView


def _has_mod_permission(interaction: discord.Interaction, mod_role_id: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return mod_role_id in [str(r.id) for r in interaction.user.roles]


@app_commands.command(name="assign_thread", description="Assign a vision thread to a player")
@app_commands.describe(
    player="The player to receive the thread",
    motif="The recurring motif to weave into their visions",
    duration_nights="How many nights the thread lasts",
)
async def assign_thread(
    interaction: discord.Interaction,
    player: discord.Member,
    motif: str,
    duration_nights: app_commands.Range[int, 1, 30],
) -> None:
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

    user_id = str(player.id)
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = db.get_active_thread(guild_id, user_id)

    if existing:
        embed = discord.Embed(
            title="⚠️ Active Thread Exists",
            description=(
                f"**{player.display_name}** already has an active vision thread.\n\n"
                f"Current motif: *{existing['motif']}*\n"
                f"Type: {'ST Assigned' if existing['is_st_assigned'] else 'Auto'}\n\n"
                f"Overwrite with: *{motif}* ({duration_nights} nights)?"
            ),
            color=0xFF8C00,
        )
        view = ConfirmOverwriteView(guild_id, user_id, motif, duration_nights, now_iso)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        db.create_thread(guild_id, user_id, motif, duration_nights, True, now_iso)
        await interaction.response.send_message(
            f"Thread assigned to **{player.display_name}**.\n"
            f"Motif: *{motif}*\n"
            f"Duration: {duration_nights} nights.\n"
            f"*(Player has not been notified.)*",
            ephemeral=True,
        )
