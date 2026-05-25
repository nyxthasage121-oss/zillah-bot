import discord
from discord import app_commands

import db


@app_commands.command(name="setup", description="Initialize Zillah for this server")
@app_commands.describe(
    auspex_role="The role that grants access to /premonition",
    mod_role="The role that grants access to ST commands",
)
async def setup(
    interaction: discord.Interaction,
    auspex_role: discord.Role,
    mod_role: discord.Role,
) -> None:
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Only server administrators can run /setup.", ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    db.upsert_server_config(guild_id, str(auspex_role.id), str(mod_role.id))
    db.reset_vision_weights(guild_id)
    db.reset_thread_pool(guild_id)

    await interaction.response.send_message(
        f"Zillah is configured.\n"
        f"Auspex role: {auspex_role.mention}\n"
        f"Mod role: {mod_role.mention}\n"
        f"Default vision weights and thread pool are ready.\n"
        f"Use /set_channel to designate the premonition channel.",
        ephemeral=True,
    )
