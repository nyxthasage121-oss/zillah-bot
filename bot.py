"""
Bot client, event handlers, and startup wiring.
"""

import os
import discord
from discord import app_commands

import clients
import db
import commands as cmd_registry


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
        await tree.sync()
        print(f"Zillah is online. Logged in as {bot.user}. Commands synced.")

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        print(f"Zillah joined a new server: {guild.name} (ID: {guild.id})")
        db.init_server(str(guild.id))

    return bot, tree
