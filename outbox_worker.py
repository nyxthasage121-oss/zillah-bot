"""Background task that drains the vision_outbox table and delivers
inflicted visions to Discord.

The web dashboard (a separate Railway process) writes rows to vision_outbox
when an ST hits "Inflict This Vision." The bot can't be reached over HTTP
from the web process, so we use the DB as the queue. This task runs inside
the bot process, polls every POLL_INTERVAL seconds, and posts each pending
vision as a Discord embed in the configured premonition channel.

Each row is marked 'sent' (with sent_at) or 'failed' (with error). Failed
rows stay in the table for manual inspection — they don't retry automatically
so a guild-config typo can't loop forever.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import discord

import db
from config import ST_EMBED_COLOR
from utils import get_clan_flavor
from views import _run_symbol_detection

logger = logging.getLogger("zillah.outbox")

POLL_INTERVAL = 5  # seconds


async def _send_one(bot: discord.Client, row: dict) -> None:
    guild_id = row["guild_id"]
    player_user_id = row["player_user_id"]

    guild = bot.get_guild(int(guild_id))
    if guild is None:
        raise RuntimeError(f"bot not in guild {guild_id}")

    config = db.get_server_config(guild_id)
    if not config or config[4] == 0:
        raise RuntimeError("guild not configured (run /setup)")

    premonition_channel_id = config[2]
    if not premonition_channel_id:
        raise RuntimeError("no premonition channel set (run /config channel)")
    channel = guild.get_channel(int(premonition_channel_id))
    if channel is None:
        raise RuntimeError(f"premonition channel {premonition_channel_id} not found")

    player = guild.get_member(int(player_user_id))
    if player is None:
        raise RuntimeError(f"player {player_user_id} not in guild")

    clan_flavor = get_clan_flavor(player.roles)
    body = row["body"]
    desc = f"*{clan_flavor}*\n\n*{body}*" if clan_flavor else f"*{body}*"
    embed = discord.Embed(description=desc, color=ST_EMBED_COLOR)
    embed.set_footer(text=f"{row['vision_type']} · From the Codex")
    embed.set_author(name=player.display_name)

    await channel.send(embed=embed)

    now_iso = datetime.now(timezone.utc).isoformat()
    db.save_vision(
        guild_id, player_user_id, row["vision_type"], body, now_iso,
        is_st_triggered=True,
    )
    asyncio.create_task(_run_symbol_detection(guild_id, player_user_id))


async def run(bot: discord.Client) -> None:
    """Loop until the bot shuts down. Errors on individual rows are logged
    and marked on the row; loop-level errors are logged and swallowed so a
    single bad poll cycle doesn't kill the worker."""
    await bot.wait_until_ready()
    logger.info("outbox worker started (poll every %ss)", POLL_INTERVAL)

    while not bot.is_closed():
        try:
            rows = await asyncio.to_thread(db.drain_outbox_pending, 10)
            for row in rows:
                try:
                    await _send_one(bot, row)
                    db.mark_outbox_sent(row["id"], datetime.now(timezone.utc).isoformat())
                    logger.info(
                        "delivered vision id=%s to player=%s in guild=%s",
                        row["id"], row["player_user_id"], row["guild_id"],
                    )
                except Exception as e:
                    logger.error("outbox row %s failed: %s", row["id"], e, exc_info=True)
                    db.mark_outbox_failed(row["id"], str(e)[:500])
        except Exception:
            logger.exception("outbox poll cycle failed")

        await asyncio.sleep(POLL_INTERVAL)
