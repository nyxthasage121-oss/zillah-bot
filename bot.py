# ── IMPORTS ──────────────────────────────────────────────────────────────────
# discord is the main library. We need two things from it:
#   - discord itself, for types and constants we'll use later
#   - app_commands, which is the system that handles slash commands
import discord
from discord import app_commands

# os lets us read environment variables — that's how we get our secret token
# without hardcoding it into the file
import os

# dotenv reads our .env file and loads those variables into the environment
# so os.getenv() can find them
from dotenv import load_dotenv

# ── LOAD ENVIRONMENT VARIABLES ───────────────────────────────────────────────
# This reads your .env file. Must happen before we try to use any secrets.
load_dotenv()

# ── INTENTS ──────────────────────────────────────────────────────────────────
# Intents tell Discord what events your bot wants to receive.
# Think of them as permissions — Discord won't send you events
# you haven't declared you want.
# default() gives us a safe starting set.
# members=True lets us check what roles a user has.
intents = discord.Intents.default()
intents.members = True

# ── BOT OBJECT ───────────────────────────────────────────────────────────────
# This creates the bot client — the object that represents Zillah.
# Everything the bot does goes through this object.
bot = discord.Client(intents=intents)

# This is the slash command system, attached to our bot.
# Every /command we build gets registered through this object.
tree = app_commands.CommandTree(bot)

# ── EVENTS ───────────────────────────────────────────────────────────────────
# @bot.event means "run this function when this Discord event happens"
# on_ready fires once, when the bot successfully connects to Discord.
@bot.event
async def on_ready():
    # Sync our slash commands with Discord so they show up in the UI.
    # This tells Discord "here are all the /commands this bot supports."
    await tree.sync()
    # Print to console so we know it worked. Railway shows this in logs.
    print(f"Zillah is online. Logged in as {bot.user}")

# ── ON GUILD JOIN ─────────────────────────────────────────────────────────────
# This fires every time Zillah is added to a new Discord server.
# "Guild" is Discord's internal word for a server.
# We'll use this later to create a blank config row for the new server.
# For now it just prints so we can see it working.
@bot.event
async def on_guild_join(guild):
    print(f"Zillah joined a new server: {guild.name} (ID: {guild.id})")

# ── RUN ───────────────────────────────────────────────────────────────────────
# This starts the bot and keeps it running.
# os.getenv("DISCORD_TOKEN") reads the token from your .env file.
# If the token is missing this will raise a clear error.
bot.run(os.getenv("DISCORD_TOKEN"))