import os
from dotenv import load_dotenv

load_dotenv()

from bot import create_bot  # noqa: E402 — must load .env before importing bot

bot, _ = create_bot()
bot.run(os.getenv("DISCORD_TOKEN"))
