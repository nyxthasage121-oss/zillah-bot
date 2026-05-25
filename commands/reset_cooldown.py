from datetime import datetime, timezone

import discord
from discord import app_commands

import db


def _has_mod_permission(interaction: discord.Interaction, mod_role_id: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return mod_role_id in [str(r.id) for r in interaction.user.roles]


@app_commands.command(
    name="reset_cooldown",
    description="Reset a player's vision uses so they can seek visions again this night",
)
@app_commands.describe(player="The player whose cooldown to reset")
async def reset_cooldown(
    interaction: discord.Interaction,
    player: discord.Member,
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

    now_iso = datetime.now(timezone.utc).isoformat()
    cooldown = db.get_cooldown(guild_id, str(player.id))

    if cooldown and cooldown[0] > 0:
        db.reset_cooldown(guild_id, str(player.id), now_iso)
        await interaction.response.send_message(
            f"The veil parts once more. **{player.display_name}**'s sight has been restored.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f"**{player.display_name}** has no uses recorded this night — they're already free to seek visions.",
            ephemeral=True,
        )
