"""Thin async wrappers around the Discord REST API for OAuth + member lookups."""
import os
import httpx
from urllib.parse import urlencode

from dashboard.config import (
    DISCORD_API_BASE,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
    DISCORD_OAUTH_SCOPES,
)


def _bot_headers() -> dict[str, str]:
    """Headers for endpoints that require the bot token, not an OAuth user token."""
    token = os.getenv("DISCORD_TOKEN", "")
    return {"Authorization": f"Bot {token}"}


def authorize_url(state: str) -> str:
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": DISCORD_OAUTH_SCOPES,
        "state": state,
        "prompt": "none",
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return r.json()


async def fetch_me(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()


async def fetch_my_guilds(access_token: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(
            f"{DISCORD_API_BASE}/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()


async def fetch_my_member(access_token: str, guild_id: str) -> dict | None:
    """Returns the user's member object in `guild_id`, or None if the bot
    can't see them. Requires the guilds.members.read scope."""
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(
            f"{DISCORD_API_BASE}/users/@me/guilds/{guild_id}/member",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


# ── bot-token endpoints (server-side, not OAuth) ─────────────────────────────

async def fetch_guild_roles(guild_id: str) -> list[dict]:
    """List all roles in a guild. Used to map role IDs → role names."""
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/roles",
            headers=_bot_headers(),
        )
        r.raise_for_status()
        return r.json()


async def fetch_guild_members(guild_id: str, limit: int = 1000) -> list[dict]:
    """List members of a guild. Requires the bot's privileged GUILD_MEMBERS intent
    (already enabled in bot.py). Default limit is the Discord max per request;
    chronicles larger than that would need pagination."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members",
            headers=_bot_headers(),
            params={"limit": limit},
        )
        r.raise_for_status()
        return r.json()
