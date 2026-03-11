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

    # ── COMMANDS ──────────────────────────────────────────────────────────────────

# ── /setup ────────────────────────────────────────────────────────────────────
# Initializes Zillah for a server. Must be run before any other commands work.
# Only users with Discord Administrator permissions can run this.
# Takes two arguments: the Auspex role and the Mod/ST role.
@tree.command(name="setup", description="Initialize Zillah for this server")
@app_commands.describe(
    auspex_role="The role that grants access to /premonition",
    mod_role="The role that grants access to ST commands"
)
async def setup(interaction: discord.Interaction, auspex_role: discord.Role, mod_role: discord.Role):
    
    # Check if the user has Administrator permissions.
    # This is the only command that checks Discord's built-in permissions
    # instead of the server's configured mod_role, because mod_role
    # doesn't exist yet when setup is being run for the first time.
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Only server administrators can run /setup.", 
            ephemeral=True
        )
        return

    # Get the guild_id — this is Discord's unique ID for this server.
    # Every database operation uses this to keep servers separate.
    guild_id = interaction.guild_id

    # Connect to the database.
    conn = sqlite3.connect("zillah.db")
    cursor = conn.cursor()

    # Insert or update the server config row for this guild.
    # INSERT OR REPLACE means: if a row with this guild_id already exists,
    # replace it. If it doesn't exist, create it.
    # This means /setup can be safely run again to reset configuration.
    cursor.execute("""
        INSERT OR REPLACE INTO server_config 
        (guild_id, auspex_role_id, mod_role_id, is_configured)
        VALUES (?, ?, ?, 1)
    """, (guild_id, auspex_role.id, mod_role.id))

    # Populate vision_weights with default values for this server.
    # We delete existing weights first so re-running /setup resets them.
    cursor.execute("DELETE FROM vision_weights WHERE guild_id = ?", (guild_id,))
    
    # Default vision types and their weights.
    # Higher number = more likely to appear.
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

    # Insert each vision type with its default weight for this server.
    for vision_type, weight in default_weights:
        cursor.execute("""
            INSERT INTO vision_weights (guild_id, vision_type, weight)
            VALUES (?, ?, ?)
        """, (guild_id, vision_type, weight))

    # Populate the thread pool with default motifs for this server.
    # These are the symbols Zillah can randomly assign as Vision Threads.
    cursor.execute("DELETE FROM thread_pool WHERE guild_id = ?", (guild_id,))

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
        cursor.execute("""
            INSERT INTO thread_pool (guild_id, motif)
            VALUES (?, ?)
        """, (guild_id, motif))

    # Save everything and close the connection.
    conn.commit()
    conn.close()

    # Confirm to the admin that setup is complete.
    # ephemeral=True means only they can see this response.
    await interaction.response.send_message(
        f"Zillah is configured.\n"
        f"Auspex role: {auspex_role.mention}\n"
        f"Mod role: {mod_role.mention}\n"
        f"Default vision weights and thread pool are ready.\n"
        f"Use /set_channel to designate the premonition channel.",
        ephemeral=True
    )
# ── /set_channel ──────────────────────────────────────────────────────────────
# Sets the channel where /premonition is active for this server.
# Only users with the configured mod_role can run this.
@tree.command(name="set_channel", description="Set the channel where /premonition is active")
@app_commands.describe(
    channel="The channel where players will use /premonition"
)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    guild_id = interaction.guild_id

    # Connect and check if this server has been configured.
    # We'll reuse this pattern in every command — always check
    # if /setup has been run before doing anything else.
    conn = sqlite3.connect("zillah.db")
    cursor = conn.cursor()

    cursor.execute("SELECT mod_role_id, is_configured FROM server_config WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()

    # If no row exists or is_configured is 0, setup hasn't been run.
    if not row or row[1] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True
        )
        conn.close()
        return

    # Check if the user has the mod role for this server.
    # row[0] is the mod_role_id we stored during /setup.
    mod_role_id = row[0]
    user_roles = [role.id for role in interaction.user.roles]

    if mod_role_id not in user_roles:
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )
        conn.close()
        return

    # Update the premonition_channel_id for this server.
    cursor.execute("""
        UPDATE server_config SET premonition_channel_id = ?
        WHERE guild_id = ?
    """, (channel.id, guild_id))

    conn.commit()
    conn.close()

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