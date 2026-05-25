import discord
from discord import app_commands

import db
from config import VISION_EMBED_COLOR


def _has_mod_permission(interaction: discord.Interaction, mod_role_id: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return mod_role_id in [str(r.id) for r in interaction.user.roles]


@app_commands.command(name="settings", description="View the current Zillah configuration for this server")
async def settings(interaction: discord.Interaction) -> None:
    guild_id = str(interaction.guild_id)
    config = db.get_server_config(guild_id)

    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    if not _has_mod_permission(interaction, str(config[1])):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    # Resolve mentions
    auspex_role = interaction.guild.get_role(int(config[0])) if config[0] else None
    mod_role    = interaction.guild.get_role(int(config[1])) if config[1] else None
    channel     = interaction.guild.get_channel(int(config[2])) if config[2] else None

    embed = discord.Embed(title="Zillah — Server Settings", color=VISION_EMBED_COLOR)

    embed.add_field(
        name="Roles",
        value=(
            f"Auspex: {auspex_role.mention if auspex_role else '*(not set)*'}\n"
            f"Mod: {mod_role.mention if mod_role else '*(not set)*'}"
        ),
        inline=False,
    )
    embed.add_field(
        name="Premonition Channel",
        value=channel.mention if channel else "*(any channel)*",
        inline=False,
    )
    embed.add_field(
        name="Night Cycle",
        value=(
            f"Night length: **{config[5] or 14} days**\n"
            f"Uses per night: **{config[3]}**\n"
            f"Sundown: **{config[6] or '20:00'} {config[7] or 'EST'}**"
        ),
        inline=False,
    )

    # Top vision weights
    weights = db.get_vision_weights(guild_id)
    if weights:
        total = sum(w for _, w in weights)
        top = sorted(weights, key=lambda x: -x[1])[:4]
        lines = []
        for vt, w in top:
            pct = f"{w / total * 100:.0f}%" if total else "—"
            lines.append(f"{vt}: **{pct}**")
        remainder = len(weights) - len(top)
        if remainder:
            lines.append(f"*+ {remainder} more — see /set_weights*")
        embed.add_field(name="Vision Weights (top)", value="\n".join(lines), inline=False)

    # Thread pool size
    pool = db.get_thread_pool(guild_id)
    embed.add_field(
        name="Thread Pool",
        value=f"**{len(pool)}** motif(s) available — see /thread_pool",
        inline=False,
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)
