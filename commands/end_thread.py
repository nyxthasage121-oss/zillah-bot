import discord
from discord import app_commands

import db
from utils import has_mod_permission


@app_commands.command(name="end_thread", description="Close a player's active vision thread early")
@app_commands.describe(player="The player whose thread to close")
async def end_thread(
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

    if not has_mod_permission(interaction, str(config[1])):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    thread = db.get_active_thread(guild_id, str(player.id))
    if not thread:
        await interaction.response.send_message(
            f"**{player.display_name}** has no active vision thread.",
            ephemeral=True,
        )
        return

    db.deactivate_thread(guild_id, str(player.id))
    source = "ST-assigned" if thread["is_st_assigned"] else "auto-triggered"
    await interaction.response.send_message(
        f"Thread closed for **{player.display_name}**.\n"
        f"The {source} motif *{thread['motif']}* will no longer appear in their visions.",
        ephemeral=True,
    )
