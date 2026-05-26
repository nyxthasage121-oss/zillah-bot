import discord
from discord import app_commands

import db


@app_commands.command(name="channel", description="Set the channel where /premonition is active")
@app_commands.describe(channel="The channel where players will use /premonition")
async def set_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)

    # config indices: auspex_role_id[0], mod_role_id[1], premonition_channel_id[2],
    #                 uses_per_night[3], is_configured[4], night_length_days[5]
    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    mod_role_id = str(config[1])
    user_role_ids = [str(r.id) for r in interaction.user.roles]
    is_admin = interaction.user.guild_permissions.administrator

    if not (is_admin or mod_role_id in user_role_ids):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    db.set_premonition_channel(guild_id, str(channel.id))

    await interaction.response.send_message(
        f"Premonition channel set to {channel.mention}.", ephemeral=True
    )
