import re

import discord
from discord import app_commands

import db


def _has_mod_permission(interaction: discord.Interaction, mod_role_id: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return mod_role_id in [str(r.id) for r in interaction.user.roles]


@app_commands.command(name="set_cooldown", description="Adjust cooldown and night length settings")
@app_commands.describe(
    night_length_days="How many days constitute one 'night' for cooldown resets",
    uses_per_night="How many times per night a player may use /premonition",
    sundown_time="Time of day cooldowns reset, in HH:MM format (e.g. 20:00)",
    sundown_timezone="Timezone for the reset time (e.g. EST, UTC, PST)",
)
async def set_cooldown(
    interaction: discord.Interaction,
    night_length_days: app_commands.Range[int, 1, 90] | None = None,
    uses_per_night: app_commands.Range[int, 1, 10] | None = None,
    sundown_time: str | None = None,
    sundown_timezone: str | None = None,
) -> None:
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

    # Validate sundown_time format before writing to DB
    if sundown_time is not None:
        if not re.fullmatch(r"\d{1,2}:\d{2}", sundown_time):
            await interaction.response.send_message(
                "Invalid time format — use `HH:MM` (e.g. `20:00` for 8 pm).", ephemeral=True
            )
            return
        try:
            h, m = (int(x) for x in sundown_time.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Invalid time — hours must be 0–23 and minutes 0–59.", ephemeral=True
            )
            return

    if all(v is None for v in (night_length_days, uses_per_night, sundown_time, sundown_timezone)):
        await interaction.response.send_message(
            "Provide at least one setting to update.", ephemeral=True
        )
        return

    db.update_cooldown_config(
        guild_id,
        night_length_days=night_length_days,
        uses_per_night=uses_per_night,
        sundown_time=sundown_time,
        sundown_timezone=sundown_timezone,
    )

    # Confirm with the current settings.
    updated = db.get_server_config(guild_id)
    lines = [
        f"Night length: **{updated[5]} days**",
        f"Uses per night: **{updated[3]}**",
        f"Sundown time: **{updated[6] or '20:00'}**",
        f"Sundown timezone: **{updated[7] or 'EST'}**",
    ]
    await interaction.response.send_message(
        "Cooldown settings updated.\n" + "\n".join(lines), ephemeral=True
    )
