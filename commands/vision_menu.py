import discord
from discord import app_commands

import db
from config import VISION_EMBED_COLOR
from menu_views import MainMenuView


@app_commands.command(name="visionmenu", description="Open the Zillah vision menu")
async def visionmenu(interaction: discord.Interaction) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)
    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="🌙 Zillah",
        description="What do you seek, Kindred?",
        color=VISION_EMBED_COLOR,
    )
    await interaction.response.send_message(embed=embed, view=MainMenuView(), ephemeral=True)
