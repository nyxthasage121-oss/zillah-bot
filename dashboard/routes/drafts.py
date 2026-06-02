"""Drafts + inflict (outbox) endpoints.

These are the HTMX-targeted routes. Save Draft → POST /drafts. Inflict →
POST /inflict (writes to vision_outbox; the bot's worker drains it and
posts the actual Discord embed). Both return small HTML partials that
HTMX swaps into the page, OR an X-Codex-Toast response header that the
client surfaces via Alpine.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

import db
from dashboard import auth
from dashboard.app import templates

logger = logging.getLogger("dashboard.drafts")
router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _toast_response(message: str, status_code: int = 200, extra_headers: dict | None = None) -> Response:
    """Empty-body response that the Alpine `htmx:afterRequest` handler turns
    into a toast via the X-Codex-Toast header. Keeps the wire format trivial."""
    headers = {"X-Codex-Toast": message}
    if extra_headers:
        headers.update(extra_headers)
    return Response(status_code=status_code, headers=headers)


@router.post("/g/{guild_id}/kindred/{player_user_id}/drafts", response_class=HTMLResponse)
async def create_or_update_draft(
    request: Request,
    guild_id: str,
    player_user_id: str,
    vision_type: str = Form(...),
    body: str = Form(...),
    draft_id: str | None = Form(None),
):
    user = auth.require_login(request)
    auth.require_guild_access(request, guild_id)
    now = _now_iso()

    if draft_id:
        await asyncio.to_thread(db.update_draft, int(draft_id), vision_type, body, now)
        new_id = int(draft_id)
        message = "Draft inscribed in the Codex"
    else:
        new_id = await asyncio.to_thread(
            db.create_draft, guild_id, player_user_id, str(user["id"]), vision_type, body, now,
        )
        message = "Draft inscribed in the Codex"

    drafts = await asyncio.to_thread(db.list_drafts_for_player, guild_id, player_user_id)
    return templates.TemplateResponse(
        request,
        "_drafts_list.html",
        {
            "drafts": drafts,
            "guild_id": guild_id,
            "player_user_id": player_user_id,
            "first_name": (request.query_params.get("first_name") or "this Kindred"),
        },
        headers={"X-Codex-Toast": message, "X-Codex-Draft-Id": str(new_id)},
    )


@router.delete("/g/{guild_id}/drafts/{draft_id}", response_class=Response)
async def delete_draft(request: Request, guild_id: str, draft_id: int):
    auth.require_login(request)
    auth.require_guild_access(request, guild_id)
    await asyncio.to_thread(db.delete_draft, draft_id)
    return _toast_response("Draft burned")


@router.post("/g/{guild_id}/kindred/{player_user_id}/inflict", response_class=Response)
async def inflict_vision(
    request: Request,
    guild_id: str,
    player_user_id: str,
    vision_type: str = Form(...),
    body: str = Form(...),
    draft_id: str | None = Form(None),
):
    user = auth.require_login(request)
    auth.require_guild_access(request, guild_id)
    if not body.strip():
        raise HTTPException(400, "An empty vision cannot be inflicted.")

    now = _now_iso()
    await asyncio.to_thread(
        db.enqueue_inflict, guild_id, player_user_id, str(user["id"]),
        vision_type, body, now,
    )
    # Burn the source draft if there was one — the chronicle remembers, the draft doesn't need to.
    if draft_id:
        await asyncio.to_thread(db.delete_draft, int(draft_id))

    return _toast_response("Vision inflicted · the bot will deliver it shortly")
