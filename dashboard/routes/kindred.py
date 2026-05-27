"""Kindred roster + vision editor pages."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

import db
from dashboard import auth, data
from dashboard.app import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = auth.session_user(request)
    if not user:
        return templates.TemplateResponse(request, "login.html", {"reason": None})
    guilds = auth.session_guilds(request)
    if not guilds:
        return templates.TemplateResponse(request, "no_access.html", {})
    # Default to the first accessible guild for now; later this becomes a picker.
    return await kindred_list(request, guild_id=guilds[0]["id"])


@router.get("/g/{guild_id}/kindred", response_class=HTMLResponse)
async def kindred_list(request: Request, guild_id: str):
    auth.require_login(request)
    guild = auth.require_guild_access(request, guild_id)
    roster = data.list_kindred(guild_id)
    return templates.TemplateResponse(
        request,
        "kindred_list.html",
        {
            "guild": guild,
            "user": auth.session_user(request),
            "all_guilds": auth.session_guilds(request),
            "roster": roster,
            "clan_labels": data.CLAN_LABELS,
        },
    )


@router.get("/g/{guild_id}/kindred/{user_id}/edit", response_class=HTMLResponse)
async def kindred_editor(request: Request, guild_id: str, user_id: str):
    auth.require_login(request)
    guild = auth.require_guild_access(request, guild_id)
    detail = data.get_kindred(guild_id, user_id)
    if not detail:
        raise HTTPException(404, "No such Kindred in this domain.")
    # Raw DB rows for the _drafts_list partial (column shape matches what HTMX
    # responses return, so the initial render and the post-save swap use the
    # exact same template).
    initial_drafts = db.list_drafts_for_player(guild_id, user_id)
    return templates.TemplateResponse(
        request,
        "editor.html",
        {
            "guild": guild,
            "user": auth.session_user(request),
            "all_guilds": auth.session_guilds(request),
            "k": detail,
            "initial_drafts": initial_drafts,
            "vision_types": data.VISION_TYPES,
            "clan_labels": data.CLAN_LABELS,
        },
    )


@router.get("/no-access", response_class=HTMLResponse)
async def no_access(request: Request):
    return templates.TemplateResponse(request, "no_access.html", {
        "user": auth.session_user(request),
    })
