import discord
from discord import app_commands

import db
from views import JournalView


@app_commands.command(name="myjournal", description="Open your full journal — visions and recurring symbols")
async def my_journal(interaction: discord.Interaction) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)

    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    view = JournalView(guild_id=guild_id, user_id=str(interaction.user.id))
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
