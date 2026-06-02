"""
Bot client, event handlers, and startup wiring.
"""

import logging
import os
import discord
from discord import app_commands

import asyncio

import clients
import db
import commands as cmd_registry
import outbox_worker

logger = logging.getLogger("zillah.bot")


def create_bot() -> tuple[discord.Client, app_commands.CommandTree]:
    intents = discord.Intents.default()
    intents.members = True

    bot = discord.Client(intents=intents)
    tree = app_commands.CommandTree(bot)

    clients.init(os.getenv("ANTHROPIC_API_KEY"))
    cmd_registry.register_all(tree)

    @bot.event
    async def on_ready() -> None:
        db.setup_database()
        # Guard tree.sync() to only run once on initial startup. discord.py
        # fires on_ready on every reconnect; each tree.sync() is a heavy
        # PUT-per-guild that, accumulated, can trip Cloudflare's 1015
        # IP-level rate limit on discord.com.
        if not getattr(bot, "_synced", False):
            await tree.sync()
            bot._synced = True
        # Spawn the outbox worker once, on first ready. Subsequent ready events
        # (after a reconnect) shouldn't start a second copy.
        if not getattr(bot, "_outbox_started", False):
            asyncio.create_task(outbox_worker.run(bot))
            bot._outbox_started = True
        logger.info("Zillah is online. Logged in as %s.", bot.user)

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        logger.info("Joined new server: %s (ID: %s)", guild.name, guild.id)
        db.init_server(str(guild.id))

    @tree.error
    async def on_app_command_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Global fallback: log the error and send the user a friendly message."""
        cmd_name = interaction.command.name if interaction.command else "unknown"
        logger.error(
            "Unhandled error in /%s (user=%s guild=%s): %s",
            cmd_name,
            interaction.user,
            interaction.guild_id,
            error,
            exc_info=error,
        )
        msg = "Something went wrong. Please try again in a moment."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass  # best-effort — don't let the error handler itself crash

    return bot, tree
