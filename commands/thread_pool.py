import discord
from discord import app_commands

import db
from utils import has_mod_permission
from views import ThreadPoolView


@app_commands.command(name="thread_pool", description="View and manage the vision thread pool")
async def thread_pool(interaction: discord.Interaction) -> None:
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

    pool = db.get_thread_pool(guild_id)
    view = ThreadPoolView(guild_id, pool)
    await interaction.response.send_message(
        embed=ThreadPoolView.build_embed(pool), view=view, ephemeral=True
    )
