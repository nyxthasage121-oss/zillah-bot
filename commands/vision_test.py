import asyncio
import functools
import logging
import random
from typing import Literal

import discord
from discord import app_commands

import clients
import db
from commands.premonition import build_vision_prompt
from config import CLAUDE_MODEL, VISION_EMBED_COLOR, VISION_ALL_TYPES
from utils import get_clan_flavor, has_mod_permission

logger = logging.getLogger("zillah.commands.vision_test")

# All vision types available for explicit selection (Lucid excluded — interactive only)
_TESTABLE_TYPES = [t for t in VISION_ALL_TYPES if t != "Lucid Vision"]

VisionTypeChoice = Literal[
    "Random (weighted)", "Standard Vision", "Glitch Vision", "Echo Vision",
    "Resonance Bleed", "Nightmare Bleed", "The Witness", "The Warning",
    "Retrocognition Surge",
]


@app_commands.command(
    name="test",
    description="Generate a test vision — bypasses all player checks, not saved to history",
)
@app_commands.describe(
    vision_type="Vision type to test, or Random for weighted selection (default: Random)",
)
async def vision_test(
    interaction: discord.Interaction,
    vision_type: VisionTypeChoice = "Random (weighted)",
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

    # Resolve vision type
    if vision_type == "Random (weighted)":
        weights_rows = db.get_vision_weights(guild_id)
        if weights_rows:
            types, weights = zip(*weights_rows)
            # Exclude Lucid Vision from random selection (interactive, can't test easily)
            filtered = [(t, w) for t, w in zip(types, weights) if t != "Lucid Vision"]
            if filtered:
                types, weights = zip(*filtered)
                chosen_type = random.choices(types, weights=weights, k=1)[0]
            else:
                chosen_type = random.choice(_TESTABLE_TYPES)
        else:
            chosen_type = random.choice(_TESTABLE_TYPES)
    else:
        chosen_type = vision_type

    await interaction.response.defer(ephemeral=True)

    try:
        response = await asyncio.to_thread(
            functools.partial(
                clients.client.messages.create,
                model=CLAUDE_MODEL,
                max_tokens=300,
                messages=[{"role": "user", "content": build_vision_prompt(chosen_type, None)}],
            )
        )
        vision_text = response.content[0].text
    except Exception as e:
        logger.error("vision test generation error: %s", e, exc_info=True)
        await interaction.followup.send(
            "The test vision failed to generate. Check the logs.", ephemeral=True
        )
        return

    # Apply clan flavor if the tester happens to have a clan role
    clan_flavor = get_clan_flavor(interaction.user.roles)
    desc = f"*{clan_flavor}*\n\n*{vision_text}*" if clan_flavor else f"*{vision_text}*"

    embed = discord.Embed(description=desc, color=VISION_EMBED_COLOR)
    embed.set_footer(text=f"{chosen_type} · Test — not saved, cooldown not affected")
    embed.set_author(name=interaction.user.display_name)

    await interaction.followup.send(embed=embed, ephemeral=True)
