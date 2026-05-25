import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging before anything else imports discord or the bot modules.
# Railway surfaces these in its log viewer with timestamps automatically.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Quieten discord.py's very chatty gateway debug output.
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)

from bot import create_bot  # noqa: E402 — must load .env before importing bot

bot, _ = create_bot()
bot.run(os.getenv("DISCORD_TOKEN"), log_handler=None)  # log_handler=None uses our config above
