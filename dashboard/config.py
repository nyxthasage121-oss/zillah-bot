"""Dashboard config — env vars and constants.

The dashboard is a second Railway process. It shares Turso (via the bot's
db.py) but has its own env vars for Discord OAuth and session signing.
"""
import os
import secrets

DISCORD_CLIENT_ID     = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI  = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Used to sign session cookies. In production set DASHBOARD_SESSION_SECRET on Railway.
# Falling back to a random per-process secret in dev means sessions die on restart —
# fine for development, intolerable for prod.
DASHBOARD_SESSION_SECRET = os.getenv("DASHBOARD_SESSION_SECRET") or secrets.token_urlsafe(32)

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_OAUTH_SCOPES = "identify guilds guilds.members.read"
