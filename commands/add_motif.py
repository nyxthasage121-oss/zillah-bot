import discord
from discord import app_commands

import db
from utils import has_mod_permission


@app_commands.command(name="add_motif", description="Add a custom motif to this server's thread pool")
@app_commands.describe(motif="The recurring image or sensation to add to the pool")
async def add_motif(interaction: discord.Interaction, motif: str) -> None:
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

    db.add_motif_to_pool(guild_id, motif.strip())
    await interaction.response.send_message(
        f"Motif added to the thread pool: *{motif.strip()}*", ephemeral=True
    )
