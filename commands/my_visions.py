import discord
from discord import app_commands

import db
from views import VisionHistoryView


@app_commands.command(name="myvisions", description="View your vision history for this server")
async def my_visions(interaction: discord.Interaction) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)

    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    view = VisionHistoryView(
        guild_id=guild_id,
        user_id=str(interaction.user.id),
        title="Your Vision History",
    )
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
