import asyncio
import functools
import logging
import random
from datetime import datetime, timezone
from typing import Literal, Union

import discord
from discord import app_commands

import clients
import db
from commands.premonition import build_vision_prompt
from config import CLAUDE_MODEL, ST_EMBED_COLOR, VISION_ALL_TYPES
from utils import get_clan_flavor, has_mod_permission
from views import _run_symbol_detection

logger = logging.getLogger("zillah.commands.send_vision")


VisionTypeOrRandom = Literal[
    "Random", "Standard Vision", "Glitch Vision", "Echo Vision",
    "Resonance Bleed", "Nightmare Bleed", "The Witness", "The Warning",
    "Retrocognition Surge",
]
# Note: "Lucid Vision" is intentionally excluded — it requires interactive buttons
# that can't be replicated in an ST send. Use "Random" to pick from all non-Lucid types.

VisionSource = Literal["AI Generated", "ST Written", "ST Prompted"]

# Types available for random selection — excludes Lucid Vision (interactive only)
_ST_VISION_TYPES = [t for t in VISION_ALL_TYPES if t != "Lucid Vision"]


async def _generate_vision(vision_type: str, source: str, custom_text: str | None) -> str:
    """Generate or return vision text based on source mode."""
    if source == "ST Written":
        return custom_text or ""

    if source == "ST Prompted":
        prompt = (
            "You are generating a vision for a VTM V5 play-by-post game. "
            "The Storyteller has provided specific guidance for this vision:\n\n"
            f"{custom_text}\n\n"
            "Write the vision in 2-4 atmospheric sentences. "
            "Do not include preamble or labels — just the vision text."
        )
    else:  # AI Generated
        prompt = build_vision_prompt(vision_type, None)

    response = await asyncio.to_thread(
        functools.partial(
            clients.client.messages.create,
            model=CLAUDE_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
    )
    return response.content[0].text


@app_commands.command(name="send", description="Send a vision to a player or role")
@app_commands.describe(
    target="The player or role to receive the vision",
    vision_type="Vision type (or Random for weighted selection)",
    source="How the vision content is generated",
    custom_text="Vision text (ST Written) or custom prompt (ST Prompted) — leave blank for AI Generated",
)
async def send_vision(
    interaction: discord.Interaction,
    target: Union[discord.Member, discord.Role],
    vision_type: VisionTypeOrRandom,
    source: VisionSource,
    custom_text: str | None = None,
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

    if source in ("ST Written", "ST Prompted") and not custom_text:
        await interaction.response.send_message(
            f"A `custom_text` value is required for source **{source}**.", ephemeral=True
        )
        return

    # Resolve target players
    auspex_role_id = str(config[0])
    if isinstance(target, discord.Role):
        players = [
            m for m in target.members
            if auspex_role_id in [str(r.id) for r in m.roles]
        ]
        if not players:
            await interaction.response.send_message(
                "No members of that role have the Auspex role.", ephemeral=True
            )
            return
    else:
        players = [target]

    # Determine the posting channel
    premonition_channel_id = config[2]
    if premonition_channel_id:
        post_channel = interaction.guild.get_channel(int(premonition_channel_id))
    else:
        post_channel = interaction.channel

    if not post_channel:
        await interaction.response.send_message(
            "Could not find the premonition channel. Check /set_channel.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    now = datetime.now(timezone.utc)
    sent = 0
    errors = 0

    for player in players:
        chosen_type = random.choice(_ST_VISION_TYPES) if vision_type == "Random" else vision_type

        try:
            vision_text = await _generate_vision(chosen_type, source, custom_text)
        except Exception as e:
            logger.error("send_vision generation error for %s: %s", player.id, e, exc_info=True)
            errors += 1
            continue

        clan_flavor = get_clan_flavor(player.roles)
        desc = f"*{clan_flavor}*\n\n*{vision_text}*" if clan_flavor else f"*{vision_text}*"
        embed = discord.Embed(description=desc, color=ST_EMBED_COLOR)
        embed.set_footer(text=f"{chosen_type} · ST Sent")
        embed.set_author(name=player.display_name)

        try:
            await post_channel.send(embed=embed)
        except Exception as e:
            logger.error("send_vision post error for %s: %s", player.id, e, exc_info=True)
            errors += 1
            continue

        db.save_vision(
            guild_id, str(player.id), chosen_type, vision_text, now.isoformat(),
            is_st_triggered=True,
        )
        asyncio.create_task(_run_symbol_detection(guild_id, str(player.id)))
        sent += 1

    summary = f"Vision(s) sent: {sent}"
    if errors:
        summary += f" | Errors: {errors}"
    await interaction.followup.send(summary, ephemeral=True)
