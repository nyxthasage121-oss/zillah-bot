# ── IMPORTS ──────────────────────────────────────────────────────────────────
# discord is the main library. We need two things from it:
#   - discord itself, for types and constants we'll use later
#   - app_commands, which is the system that handles slash commands
import discord
from discord import app_commands

# os lets us read environment variables — that's how we get our secret token
# without hardcoding it into the file
import os
import sqlite3

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

# ── DATABASE ──────────────────────────────────────────────────────────────────
# This function creates all of Zillah's database tables if they don't exist.
# "IF NOT EXISTS" means it's safe to run every time the bot starts —
# it won't wipe your data if the tables are already there.
def setup_database():
    # Connect to the database file. If zillah.db doesn't exist yet,
    # sqlite3 creates it automatically.
    conn = sqlite3.connect("zillah.db")
    
    # A cursor is what actually runs SQL commands.
    # Think of conn as the connection to the database,
    # and cursor as the pen you write with.
    cursor = conn.cursor()

    # ── SERVER CONFIG ──────────────────────────────────────────────────────
    # One row per Discord server. Stores all the settings for that server.
    # guild_id is the Discord server's unique ID — this is how we keep
    # every server's data completely separate from every other server.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id INTEGER PRIMARY KEY,
            auspex_role_id INTEGER,
            mod_role_id INTEGER,
            premonition_channel_id INTEGER,
            night_length_days INTEGER DEFAULT 14,
            sundown_time TEXT DEFAULT '20:00',
            sundown_timezone TEXT DEFAULT 'EST',
            uses_per_night INTEGER DEFAULT 1,
            is_configured INTEGER DEFAULT 0
        )
    """)

    # ── VISION WEIGHTS ─────────────────────────────────────────────────────
    # One row per vision type per server.
    # Stores how likely each vision type is to appear.
    # Higher weight = more likely. Weight 0 = disabled for that server.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vision_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            vision_type TEXT,
            weight INTEGER DEFAULT 10
        )
    """)

    # ── PLAYER COOLDOWNS ───────────────────────────────────────────────────
    # Tracks how many visions each player has used this night
    # and when the last reset happened.
    # guild_id + user_id together identify one player on one server.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_cooldowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            uses_this_night INTEGER DEFAULT 0,
            last_reset_timestamp TEXT
        )
    """)

    # ── VISION HISTORY ─────────────────────────────────────────────────────
    # Every vision ever delivered gets saved here.
    # is_st_triggered tells us if a Storyteller sent it manually.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            vision_type TEXT,
            vision_text TEXT,
            timestamp TEXT,
            is_st_triggered INTEGER DEFAULT 0
        )
    """)

    # ── VISION THREADS ─────────────────────────────────────────────────────
    # Tracks active Vision Threads assigned to players.
    # is_active lets us mark a thread as expired without deleting it.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vision_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            motif TEXT,
            start_timestamp TEXT,
            duration_nights INTEGER,
            is_active INTEGER DEFAULT 1,
            is_st_assigned INTEGER DEFAULT 0
        )
    """)

    # ── DETECTED SYMBOLS ───────────────────────────────────────────────────
    # Stores recurring motifs the AI has detected across a player's visions.
    # This is what powers the symbol tracker in /my_journal.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detected_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            symbol TEXT,
            first_seen TEXT,
            last_seen TEXT,
            occurrence_count INTEGER DEFAULT 1
        )
    """)

    # ── THREAD POOL ────────────────────────────────────────────────────────
    # A pool of motifs the bot can randomly assign as Vision Threads.
    # Each server gets its own pool seeded with defaults on /setup.
    # STs can add custom motifs to their server's pool later.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thread_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            motif TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Save all the changes and close the connection.
    # Without commit() nothing actually gets written to the file.
    conn.commit()
    conn.close()
    print("Database ready.")
# ── EVENTS ───────────────────────────────────────────────────────────────────
# @bot.event means "run this function when this Discord event happens"
# on_ready fires once, when the bot successfully connects to Discord.
@bot.event
async def on_ready():
    setup_database()
    print("Database ready.")
    await tree.sync()   
    print(f"Zillah is online. Logged in as {bot.user}. Commands synced. Database ready.")

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