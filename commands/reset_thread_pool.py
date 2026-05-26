import discord
from discord import app_commands

import db
from utils import has_mod_permission


@app_commands.command(
    name="resetpool",
    description="Reset the vision thread pool to its default motifs (removes all custom entries)",
)
async def reset_thread_pool(interaction: discord.Interaction) -> None:
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

    db.reset_thread_pool(guild_id)

    await interaction.response.send_message(
        "The thread pool has been reset to its default motifs. "
        "Use `/add_motif` to add custom entries, or `/thread_pool` to review.",
        ephemeral=True,
    )
