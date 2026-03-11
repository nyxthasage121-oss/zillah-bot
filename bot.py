# ── IMPORTS ──────────────────────────────────────────────────────────────────
# discord is the main library. We need two things from it:
#   - discord itself, for types and constants we'll use later
#   - app_commands, which is the system that handles slash commands
import discord
from discord import app_commands

# os lets us read environment variables — that's how we get our secret token
# without hardcoding it into the file
import os
import libsql_experimental as libsql
import asyncio

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
# Returns a connected Turso client.
# We call this every time we need to talk to the database.
# The "with" pattern ensures the connection closes automatically when done.
def get_db():
    conn = libsql.connect(
        database=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN")
    )
    return conn

# Sets up all database tables if they don't exist yet.
# Now async because Turso requires await for all database operations.
def setup_database():
    conn = get_db()
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            vision_type TEXT,
            weight INTEGER DEFAULT 10
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_cooldowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            uses_this_night INTEGER DEFAULT 0,
            last_reset_timestamp TEXT
        )
    """)
    conn.execute("""
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
    conn.execute("""
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
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thread_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            motif TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    print("Database ready.")

    # ── COMMANDS ──────────────────────────────────────────────────────────────────

# ── /setup ────────────────────────────────────────────────────────────────────
@tree.command(name="setup", description="Initialize Zillah for this server")
@app_commands.describe(
    auspex_role="The role that grants access to /premonition",
    mod_role="The role that grants access to ST commands"
)
async def setup(interaction: discord.Interaction, auspex_role: discord.Role, mod_role: discord.Role):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Only server administrators can run /setup.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild_id
    conn = get_db()

    conn.execute(
        "INSERT OR REPLACE INTO server_config (guild_id, auspex_role_id, mod_role_id, is_configured) VALUES (?, ?, ?, 1)",
        (guild_id, auspex_role.id, mod_role.id)
    )

    conn.execute("DELETE FROM vision_weights WHERE guild_id = ?", (guild_id,)

    default_weights = [
        ("Standard Vision", 40),
        ("Lucid Vision", 15),
        ("Glitch Vision", 15),
        ("Echo Vision", 10),
        ("Resonance Bleed", 7),
        ("Nightmare Bleed", 7),
        ("The Witness", 5),
        ("The Warning", 3),
        ("Retrocognition Surge", 3),
    ]

    for vision_type, weight in default_weights:
        conn.execute(
            "INSERT INTO vision_weights (guild_id, vision_type, weight) VALUES (?, ?, ?)",
            (guild_id, vision_type, weight)
        )

    conn.execute("DELETE FROM thread_pool WHERE guild_id = ?", (guild_id,)

    default_motifs = [
        "a drowned woman with no face",
        "the smell of smoke with no source",
        "a broken clock frozen at the same hour",
        "the sound of bells that no one else hears",
        "a red door that appears in every vision",
        "a crow that watches but never moves",
        "handwriting that almost resembles your own",
        "the taste of blood that isn't yours",
        "a figure standing at the edge of every scene",
        "the feeling of being watched from below",
        "a child's laughter in empty rooms",
        "mirrors that show the wrong reflection",
    ]

    for motif in default_motifs:
        conn.execute(
            "INSERT INTO thread_pool (guild_id, motif) VALUES (?, ?)",
            (guild_id, motif)
        )

    conn.commit()

    await interaction.response.send_message(
        f"Zillah is configured.\n"
        f"Auspex role: {auspex_role.mention}\n"
        f"Mod role: {mod_role.mention}\n"
        f"Default vision weights and thread pool are ready.\n"
        f"Use /set_channel to designate the premonition channel.",
        ephemeral=True
    )

# ── /set_channel ──────────────────────────────────────────────────────────────
@tree.command(name="set_channel", description="Set the channel where /premonition is active")
@app_commands.describe(
    channel="The channel where players will use /premonition"
)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    guild_id = interaction.guild_id
    conn = get_db()

    result = conn.execute(
        "SELECT mod_role_id, is_configured FROM server_config WHERE guild_id = ?",
        (guild_id,)
    ).fetchone()

    if not result or result[1] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True
        )
        return

    mod_role_id = result[0]
    user_roles = [role.id for role in interaction.user.roles]

    if mod_role_id not in user_roles:
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )
        return
    
    conn.execute(
        "UPDATE server_config SET premonition_channel_id = ? WHERE guild_id = ?",
        (channel.id, guild_id,)
    )
    conn.commit()

    await interaction.response.send_message(
        f"Premonition channel set to {channel.mention}.",
        ephemeral=True
    )

# ── EVENTS ───────────────────────────────────────────────────────────────────
# @bot.event means "run this function when this Discord event happens"
# on_ready fires once, when the bot successfully connects to Discord.
@bot.event
async def on_ready():
    setup_database()
    await tree.sync()
    print(f"Zillah is online. Logged in as {bot.user}. Commands synced.")

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