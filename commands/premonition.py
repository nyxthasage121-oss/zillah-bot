import random
from datetime import datetime, timezone

import discord
from discord import app_commands
import anthropic

import db
from config import VISION_TYPE_DESCRIPTIONS, VISION_EMBED_COLOR, CLAUDE_MODEL

# Initialized in bot.py and injected here at startup via commands/__init__.py.
anthropic_client: anthropic.Anthropic | None = None


def _build_prompt(chosen_type: str, active_motif: str | None) -> str:
    thread_instruction = ""
    if active_motif:
        thread_instruction = (
            f"\n\nImportant: Weave a subtle, oblique reference to the following motif somewhere "
            f"into the vision. Do not make it obvious — it should feel like it might be coincidence: "
            f"{active_motif}"
        )

    return (
        "You are generating a vision for a Vampire: The Masquerade 5th Edition play-by-post game. "
        "The player has the Auspex discipline and has received a premonition.\n\n"
        f"Vision type: {chosen_type}\n\n"
        f"Vision type descriptions:\n{VISION_TYPE_DESCRIPTIONS}\n\n"
        "Generate a single vision appropriate for the type above. Write 2-4 sentences. "
        "Be evocative and atmospheric. Do not explain the vision or break immersion. "
        "Do not include any preamble or labels — just the vision text itself."
        f"{thread_instruction}"
    )


@app_commands.command(name="premonition", description="Receive a vision from beyond the veil")
async def premonition(interaction: discord.Interaction) -> None:
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    # ── 1. Server configured? ─────────────────────────────────────────────
    # config: auspex_role_id[0], mod_role_id[1], premonition_channel_id[2],
    #         uses_per_night[3], is_configured[4], night_length_days[5]
    config = db.get_server_config(guild_id)
    if not config or config[4] == 0:
        await interaction.response.send_message(
            "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
            ephemeral=True,
        )
        return

    auspex_role_id = str(config[0])
    premonition_channel_id = config[2]
    uses_per_night = config[3]
    night_length_days = config[5] or 14  # fall back to 14 if null

    # ── 2. Correct channel? ───────────────────────────────────────────────
    if premonition_channel_id and str(interaction.channel_id) != str(premonition_channel_id):
        await interaction.response.send_message(
            "Visions can only be sought in the designated channel.", ephemeral=True
        )
        return

    # ── 3. Has Auspex role? ───────────────────────────────────────────────
    user_role_ids = [str(r.id) for r in interaction.user.roles]
    if auspex_role_id not in user_role_ids:
        await interaction.response.send_message(
            "You do not possess the sight required to seek visions.", ephemeral=True
        )
        return

    # ── 4. Cooldown check ─────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    cooldown = db.get_cooldown(guild_id, user_id)
    uses_this_night = 0

    if cooldown:
        uses_this_night = cooldown[0]
        last_reset = datetime.fromisoformat(cooldown[1]) if cooldown[1] else None
        if last_reset:
            hours_elapsed = (now - last_reset).total_seconds() / 3600
            if hours_elapsed >= night_length_days * 24:
                db.reset_cooldown(guild_id, user_id, now.isoformat())
                uses_this_night = 0

    if uses_this_night >= uses_per_night:
        await interaction.response.send_message(
            "The veil does not part twice in the same night. "
            "Your sight will return when the sun next sets.",
            ephemeral=True,
        )
        return

    # ── 5. Pick vision type ───────────────────────────────────────────────
    weights_rows = db.get_vision_weights(guild_id)
    if not weights_rows:
        await interaction.response.send_message(
            "No vision types are configured. An ST needs to run /setup.", ephemeral=True
        )
        return

    vision_types, weights = zip(*weights_rows)
    chosen_type = random.choices(vision_types, weights=weights, k=1)[0]

    # ── 6. Active vision thread? ──────────────────────────────────────────
    active_motif = db.get_active_thread_motif(guild_id, user_id)

    # ── 7. Defer while Claude generates ──────────────────────────────────
    await interaction.response.defer()

    # ── 8. Generate vision ────────────────────────────────────────────────
    try:
        message = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": _build_prompt(chosen_type, active_motif)}],
        )
        vision_text = message.content[0].text
    except Exception as e:
        print(f"Anthropic API error: {e}")
        await interaction.followup.send(
            "The veil trembles but does not part. Try again in a moment.", ephemeral=True
        )
        return

    # ── 9. Persist cooldown + history ─────────────────────────────────────
    db.increment_cooldown(guild_id, user_id, now.isoformat(), exists=bool(cooldown))
    db.save_vision(guild_id, user_id, chosen_type, vision_text, now.isoformat())

    # ── 10. Post the vision ───────────────────────────────────────────────
    embed = discord.Embed(description=f"*{vision_text}*", color=VISION_EMBED_COLOR)
    embed.set_footer(text=chosen_type)
    embed.set_author(name=interaction.user.display_name)
    await interaction.followup.send(embed=embed)
