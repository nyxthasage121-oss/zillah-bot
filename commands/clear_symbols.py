import discord
from discord import app_commands

import db
from utils import has_mod_permission


@app_commands.command(
    name="clear_symbols",
    description="Clear all detected recurring symbols for a player",
)
@app_commands.describe(player="The player whose symbols to clear")
async def clear_symbols(
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

    symbols = db.get_detected_symbols(guild_id, str(player.id))
    if not symbols:
        await interaction.response.send_message(
            f"**{player.display_name}** has no detected symbols to clear.",
            ephemeral=True,
        )
        return

    count = len(symbols)
    db.clear_detected_symbols(guild_id, str(player.id))
    await interaction.response.send_message(
        f"Cleared {count} symbol(s) for **{player.display_name}**. "
        f"Their journal's symbol tab is now empty.",
        ephemeral=True,
    )
