"""FastAPI entrypoint for the Storyteller's Codex web dashboard.

Run locally:  uvicorn dashboard.app:app --reload --port 8000
Run on Railway via the Procfile `web:` line.

OAuth env vars (set on Railway):
  DISCORD_CLIENT_ID
  DISCORD_CLIENT_SECRET
  DISCORD_REDIRECT_URI         e.g. https://zillah.up.railway.app/auth/callback
  DASHBOARD_SESSION_SECRET     long random string

Shares the bot's TURSO_DATABASE_URL / TURSO_AUTH_TOKEN.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402  -- after load_dotenv + logging
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db  # noqa: E402  -- bot's db module, shared connection
from dashboard.config import DASHBOARD_SESSION_SECRET

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the schema (including the dashboard's vision_drafts/outbox tables)
    # exists. The bot process also calls this on its own startup — safe to
    # call from both, the CREATE TABLE statements are IF NOT EXISTS.
    db.setup_database()
    yield


app = FastAPI(title="Zillah · Storyteller's Codex", docs_url=None, redoc_url=None, lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=DASHBOARD_SESSION_SECRET,
    session_cookie="zillah_session",
    max_age=60 * 60 * 24 * 14,  # 14 days
    same_site="lax",
    https_only=os.getenv("RAILWAY_ENVIRONMENT") is not None,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# Routers — imported after `templates` exists because they reference it.
from dashboard.routes import auth as auth_routes  # noqa: E402
from dashboard.routes import kindred as kindred_routes  # noqa: E402
from dashboard.routes import drafts as drafts_routes  # noqa: E402

app.include_router(auth_routes.router)
app.include_router(kindred_routes.router)
app.include_router(drafts_routes.router)


# Dev-only: seed a fake session so the protected pages can be previewed
# without running through real Discord OAuth. Guarded by an env var so it
# can never accidentally ship to production.
if os.getenv("DASHBOARD_DEV_PREVIEW") == "1":
    from fastapi import Request
    from fastapi.responses import RedirectResponse

    @app.get("/_dev/seed")
    async def _dev_seed(request: Request):
        request.session["user"] = {"id": "999", "username": "amelia", "avatar": None}
        request.session["guilds"] = [{"id": "100", "name": "St. Augustine by Night", "icon": None}]
        return RedirectResponse(url="/", status_code=307)
