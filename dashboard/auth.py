"""Session + permission helpers.

A user is admitted only for guilds where:
  1. The bot has been configured (server_config row exists with is_configured = 1)
  2. The user holds the configured mod_role_id in that guild

The accessible-guild list is computed once at OAuth callback and stored in
the session. Re-login refreshes it.
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from fastapi import HTTPException, Request, status
from starlette.responses import RedirectResponse

from dashboard import discord_api


def session_user(request: Request) -> dict | None:
    """Return the logged-in user dict from session, or None."""
    return request.session.get("user")


def session_guilds(request: Request) -> list[dict]:
    """Return the list of guilds the user has ST access to (cached in session)."""
    return request.session.get("guilds", [])


def require_login(request: Request) -> dict:
    user = session_user(request)
    if not user:
        # FastAPI dependency — raising a RedirectResponse-shaped exception
        # by setting the status code lets the route handler return one cleanly.
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/auth/login"},
        )
    return user


def require_guild_access(request: Request, guild_id: str) -> dict:
    """Ensure the logged-in user has ST access to `guild_id`, return the guild dict."""
    require_login(request)
    for g in session_guilds(request):
        if str(g["id"]) == str(guild_id):
            return g
    raise HTTPException(status_code=403, detail="You are not a Storyteller in that domain.")


async def compute_accessible_guilds(access_token: str) -> list[dict]:
    """Cross-reference the user's Discord guilds against server_config and
    the per-guild mod_role_id.

    Returns a list of dicts: { id, name, icon }.

    Lazy import of db so the dashboard module can be loaded without
    Turso env vars being set (e.g. when generating docs).
    """
    from db import get_server_config  # local import to avoid circulars at boot

    user_guilds = await discord_api.fetch_my_guilds(access_token)

    async def check(g: dict) -> dict | None:
        gid = str(g["id"])
        # Bot must be configured in this guild
        cfg = await asyncio.to_thread(get_server_config, gid)
        if not cfg or cfg[4] != 1:
            return None
        mod_role_id = str(cfg[1]) if cfg[1] else None
        if not mod_role_id:
            return None
        member = await discord_api.fetch_my_member(access_token, gid)
        if not member:
            return None
        member_roles = [str(r) for r in member.get("roles", [])]
        if mod_role_id not in member_roles:
            return None
        return {"id": gid, "name": g["name"], "icon": g.get("icon")}

    results = await asyncio.gather(*(check(g) for g in user_guilds))
    return [r for r in results if r]


def login_redirect(target: str = "/") -> RedirectResponse:
    return RedirectResponse(url=f"/auth/login?next={target}", status_code=307)
