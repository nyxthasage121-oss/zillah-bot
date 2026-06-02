"""OAuth login, callback, logout."""
import logging
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from dashboard import auth, discord_api

logger = logging.getLogger("dashboard.auth")
router = APIRouter(prefix="/auth")


@router.get("/login")
async def login(request: Request, next: str = "/"):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    request.session["oauth_next"] = next
    return RedirectResponse(url=discord_api.authorize_url(state), status_code=307)


@router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None):
    expected_state = request.session.pop("oauth_state", None)
    next_url = request.session.pop("oauth_next", "/")
    if not code or not state or state != expected_state:
        return RedirectResponse(url="/auth/login", status_code=307)

    try:
        token_payload = await discord_api.exchange_code(code)
    except Exception as e:
        logger.warning("OAuth exchange failed: %s", e)
        return RedirectResponse(url="/auth/login", status_code=307)

    access_token = token_payload["access_token"]

    try:
        me = await discord_api.fetch_me(access_token)
        guilds = await auth.compute_accessible_guilds(access_token)
    except Exception as e:
        logger.warning("OAuth user fetch failed: %s", e)
        return RedirectResponse(url="/auth/login", status_code=307)

    request.session["user"] = {
        "id": str(me["id"]),
        "username": me.get("global_name") or me.get("username"),
        "avatar": me.get("avatar"),
    }
    request.session["guilds"] = guilds
    request.session["access_token"] = access_token

    if not guilds:
        return RedirectResponse(url="/no-access", status_code=307)
    return RedirectResponse(url=next_url, status_code=307)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=307)
