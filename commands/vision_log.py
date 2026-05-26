import discord
from discord import app_commands

import db
from utils import has_mod_permission
from views import VisionHistoryView


@app_commands.command(name="log", description="Look up a player's vision history")
@app_commands.describe(player="The player whose vision history to view")
async def vision_log(interaction: discord.Interaction, player: discord.Member) -> None:
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

    view = VisionHistoryView(
        guild_id=guild_id,
        user_id=str(player.id),
        title=f"Vision Log — {player.display_name}",
    )
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
