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
import random
from datetime import datetime, timezone

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
# Initialize the Anthropic client.
# This is what we use to call Claude and generate visions.
import anthropic
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── DATABASE ──────────────────────────────────────────────────────────────────
# Returns a connected Turso client.
# We call this every time we need to talk to the database.
# The "with" pattern ensures the connection closes automatically when done.
def setup_database():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id TEXT PRIMARY KEY,
            auspex_role_id TEXT,
            mod_role_id TEXT,
            premonition_channel_id TEXT,
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
            guild_id TEXT,
            vision_type TEXT,
            weight INTEGER DEFAULT 10
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_cooldowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            uses_this_night INTEGER DEFAULT 0,
            last_reset_timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            vision_type TEXT,
            vision_text TEXT,
            timestamp TEXT,
            is_st_triggered INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vision_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
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
            guild_id TEXT,
            user_id TEXT,
            symbol TEXT,
            first_seen TEXT,
            last_seen TEXT,
            occurrence_count INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thread_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            motif TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    print("Database ready.")

# ── /setup ────────────────────────────────────────────────────────────────────
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

    guild_id = str(interaction.guild_id)
    conn = get_db()

    conn.execute(
        "INSERT OR REPLACE INTO server_config (guild_id, auspex_role_id, mod_role_id, is_configured) VALUES (?, ?, ?, 1)",
        (guild_id, str(auspex_role.id), str(mod_role.id))
    )

    conn.execute("DELETE FROM vision_weights WHERE guild_id = ?", (guild_id,))

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

    conn.execute("DELETE FROM thread_pool WHERE guild_id = ?", (guild_id,))

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

    mod_role_id = int(result[0])
    user_roles = [int(r.id) for r in interaction.user.roles]
    is_admin = interaction.user.guild_permissions.administrator
    has_mod_role = mod_role_id in user_roles

    if not (is_admin or has_mod_role):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )
        return

    conn.execute(
        "UPDATE server_config SET premonition_channel_id = ? WHERE guild_id = ?",
        (str(channel.id), guild_id)
    )

    conn.commit()

    await interaction.response.send_message(
        f"Premonition channel set to {channel.mention}.",
        ephemeral=True
    )

# ── /premonition ──────────────────────────────────────────────────────────────
# The main player command. Generates an AI vision for the player.
# Checks channel, role, and cooldown before making any API calls.
@tree.command(name="premonition", description="Receive a vision from beyond the veil")
async def premonition(interaction: discord.Interaction):

    guild_id = interaction.guild_id
    user_id = interaction.user.id
    conn = get_db()

    # ── STEP 1: CHECK SERVER IS CONFIGURED ────────────────────────────────
    config = conn.execute(
        "SELECT auspex_role_id, premonition_channel_id, uses_per_night, is_configured FROM server_config WHERE guild_id = ?",
        (guild_id,)
    ).fetchone()

    if not config or config[3] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True
        )
        return

    auspex_role_id = int(config[0])
    premonition_channel_id = config[1]
    uses_per_night = config[2]

    # ── STEP 2: CHECK CHANNEL ─────────────────────────────────────────────
    # If a premonition channel has been set, only allow the command there.
    # ── STEP 2: CHECK CHANNEL ─────────────────────────────────────────────
    print(f"DEBUG channel_id from DB: {premonition_channel_id} type: {type(premonition_channel_id)}")
    print(f"DEBUG interaction.channel_id: {interaction.channel_id} type: {type(interaction.channel_id)}")
    if premonition_channel_id and str(interaction.channel_id) != str(premonition_channel_id):
        await interaction.response.send_message(
            "Visions can only be sought in the designated channel.",
            ephemeral=True
        )
        return

    # ── STEP 3: CHECK AUSPEX ROLE ─────────────────────────────────────────
    user_roles = [int(role.id) for role in interaction.user.roles]
    if auspex_role_id not in user_roles:
        await interaction.response.send_message(
            "You do not possess the sight required to seek visions.",
            ephemeral=True
        )
        return

    # ── STEP 4: CHECK COOLDOWN ────────────────────────────────────────────
    cooldown = conn.execute(
        "SELECT uses_this_night, last_reset_timestamp FROM player_cooldowns WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    ).fetchone()

    now = datetime.now(timezone.utc)

    if cooldown:
        uses_this_night = cooldown[0]
        last_reset = datetime.fromisoformat(cooldown[1]) if cooldown[1] else None

        # Check if a reset is needed based on the server's night length.
        # For now we reset if it's been more than night_length_days * 24 hours.
        # Full sundown-based reset comes later.
        if last_reset:
            hours_elapsed = (now - last_reset).total_seconds() / 3600
            night_length_hours = 14 * 24  # default 14 days in hours
            if hours_elapsed >= night_length_hours:
                # Reset the cooldown
                conn.execute(
                    "UPDATE player_cooldowns SET uses_this_night = 0, last_reset_timestamp = ? WHERE guild_id = ? AND user_id = ?",
                    (now.isoformat(), guild_id, user_id)
                )
                conn.commit()
                uses_this_night = 0

        if uses_this_night >= uses_per_night:
            await interaction.response.send_message(
                "The veil does not part twice in the same night. Your sight will return when the sun next sets.",
                ephemeral=True
            )
            return
    else:
        uses_this_night = 0

    # ── STEP 5: PICK VISION TYPE ──────────────────────────────────────────
    # Pull vision weights for this server and pick one randomly.
    weights_rows = conn.execute(
        "SELECT vision_type, weight FROM vision_weights WHERE guild_id = ?",
        (guild_id,)
    ).fetchall()

    if not weights_rows:
        await interaction.response.send_message(
            "No vision types are configured. An ST needs to run /setup.",
            ephemeral=True
        )
        return

    vision_types = [row[0] for row in weights_rows]
    weights = [row[1] for row in weights_rows]
    chosen_type = random.choices(vision_types, weights=weights, k=1)[0]

    # ── STEP 6: CHECK FOR ACTIVE VISION THREAD ────────────────────────────
    # If the player has an active Vision Thread, pass the motif to the prompt.
    thread = conn.execute(
        "SELECT motif FROM vision_threads WHERE guild_id = ? AND user_id = ? AND is_active = 1",
        (guild_id, user_id)
    ).fetchone()
    active_motif = thread[0] if thread else None

    # ── STEP 7: DEFER THE RESPONSE ────────────────────────────────────────
    # API calls take a moment. Deferring tells Discord "we're working on it"
    # so the interaction doesn't time out while we wait for Claude.
    await interaction.response.defer()

    # ── STEP 8: BUILD THE PROMPT AND CALL CLAUDE ──────────────────────────
    thread_instruction = ""
    if active_motif:
        thread_instruction = f"\n\nImportant: Weave a subtle, oblique reference to the following motif somewhere into the vision. Do not make it obvious — it should feel like it might be coincidence: {active_motif}"

    prompt = f"""You are generating a vision for a Vampire: The Masquerade 5th Edition play-by-post game. The player has the Auspex discipline and has received a premonition.

Vision type: {chosen_type}

Vision type descriptions:
- Standard Vision: An atmospheric paragraph of sensory impressions with no clear meaning. Eerie, poetic, unsettling.
- Lucid Vision: A vivid, slightly more coherent vision that feels almost meaningful but remains ambiguous.
- Glitch Vision: A corrupted, fragmented vision. Use unusual formatting — incomplete sentences, repeated words, sudden cuts. Should feel broken.
- Echo Vision: A flash of emotional residue from a place or object. Impressionistic, tied to feeling rather than sight.
- Resonance Bleed: Written in second person present tense, as if the player is accidentally experiencing someone else's emotions right now.
- Nightmare Bleed: A vision that doesn't close cleanly. Write the vision, then add a short italicized postscript suggesting it has followed them into waking.
- The Witness: Written in first person from an unknown subject's point of view. The player sees through someone else's eyes briefly.
- The Warning: A vision with directional urgency. Vague but clearly important. End with a single sentence of quiet dread.
- Retrocognition Surge: Multiple fragmented timeline impressions simultaneously. Use formatting to suggest fragmentation — dashes, breaks, incomplete images.

Generate a single vision appropriate for the type above. Write 2-4 sentences. Be evocative and atmospheric. Do not explain the vision or break immersion. Do not include any preamble or labels — just the vision text itself.{thread_instruction}"""

    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        vision_text = message.content[0].text

    except Exception as e:
        print(f"Anthropic API error: {e}")
        await interaction.followup.send(
            "The veil trembles but does not part. Try again in a moment.",
            ephemeral=True
        )
        return

    # ── STEP 9: UPDATE COOLDOWN ───────────────────────────────────────────
    if cooldown:
        conn.execute(
            "UPDATE player_cooldowns SET uses_this_night = uses_this_night + 1 WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
    else:
        conn.execute(
            "INSERT INTO player_cooldowns (guild_id, user_id, uses_this_night, last_reset_timestamp) VALUES (?, ?, 1, ?)",
            (guild_id, user_id, now.isoformat())
        )
    conn.commit()

    # ── STEP 10: SAVE TO VISION HISTORY ───────────────────────────────────
    conn.execute(
        "INSERT INTO vision_history (guild_id, user_id, vision_type, vision_text, timestamp, is_st_triggered) VALUES (?, ?, ?, ?, ?, 0)",
        (guild_id, user_id, chosen_type, vision_text, now.isoformat())
    )
    conn.commit()

    # ── STEP 11: POST THE VISION ──────────────────────────────────────────
    embed = discord.Embed(
        description=f"*{vision_text}*",
        color=0x8B0000
    )
    embed.set_footer(text=chosen_type)
    embed.set_author(name=interaction.user.display_name)

    await interaction.followup.send(embed=embed)

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