# Zillah — Claude Code Project Context

Zillah is a Discord bot for Vampire: The Masquerade 5th Edition play-by-post servers.
Players with the Auspex discipline use `/premonition` to receive AI-generated visions.
Storytellers (STs) manage settings, threads, and player history via slash commands.

---

## Tech stack

- **Discord**: discord.py 2.x, slash commands via `app_commands`, interactive UI via `discord.ui.View`
- **AI**: Anthropic Claude (`claude-sonnet-4-20250514`) — all calls use `asyncio.to_thread(functools.partial(...))` to avoid blocking
- **Database**: Turso hosted libsql via `libsql-experimental` Python package
- **Hosting**: Railway — `worker: python main.py` (Procfile)
- **Python**: 3.11+

---

## File structure

```
main.py         entry point — loads .env, configures logging, runs bot
bot.py          discord.Client setup, event handlers, global error handler (@tree.error)
clients.py      Anthropic singleton — init() called once at startup
config.py       all static constants (NIGHT_EPOCH, TIMEZONE_ALIASES, CLAN_FLAVOR, weights, etc.)
db.py           all DB query helpers + connection cache + @_with_reconnect decorator
utils.py        has_mod_permission(), resolve_timezone(), get_night_start(),
                get_elapsed_nights(), get_clan_flavor()
views.py        all discord.ui.View subclasses + background task helpers
                (LucidVisionView, JournalView, VisionHistoryView, ConfirmOverwriteView, ThreadPoolView)
commands/       one file per slash command, all registered in __init__.py
```

---

## Critical patterns — read these before making any changes

### All Discord IDs must be TEXT (never int)
Turso converts large 64-bit integers to floats, causing precision loss on snowflakes.
Always store and compare as strings: `str(role.id)`, `str(interaction.guild_id)`, etc.

### Blocking calls must use asyncio.to_thread
```python
response = await asyncio.to_thread(
    functools.partial(
        clients.client.messages.create,
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
)
```
Never call `clients.client.messages.create()` directly in an async context.

### Permission check — always import from utils, never define locally
```python
from utils import has_mod_permission
# ...
if not has_mod_permission(interaction, str(config[1])):
    await interaction.response.send_message("You don't have permission.", ephemeral=True)
    return
```

### Standard config check at the top of every command
```python
config = db.get_server_config(guild_id)
if not config or config[4] == 0:
    await interaction.response.send_message(
        "Zillah hasn't been configured yet. An administrator needs to run /setup first.",
        ephemeral=True,
    )
    return
```

### config tuple indexes
`db.get_server_config(guild_id)` returns a tuple:
| Index | Field | Type |
|-------|-------|------|
| [0] | auspex_role_id | TEXT |
| [1] | mod_role_id | TEXT |
| [2] | premonition_channel_id | TEXT |
| [3] | uses_per_night | int |
| [4] | is_configured | int (0 or 1) |
| [5] | night_length_days | int |
| [6] | sundown_time | TEXT ("HH:MM") |
| [7] | sundown_timezone | TEXT ("EST", "UTC", etc.) |

Defaults for night config: `config[5] or 14`, `config[6] or "20:00"`, `config[7] or "EST"`

### Night timing utilities (utils.py)
```python
# UTC datetime when the current night started
night_start = get_night_start(night_length_days, sundown_time, sundown_timezone)

# Number of complete sundown boundaries crossed since a given ISO timestamp
elapsed = get_elapsed_nights(start_iso, night_length_days, sundown_time, sundown_timezone)
```
Both functions are anchored to `NIGHT_EPOCH = datetime(2024, 1, 1, tzinfo=timezone.utc)` in config.py.

### DB connection
`get_db()` returns a cached connection. All public DB functions are decorated with
`@_with_reconnect` — on any error the cache is cleared and the call retries once.
`setup_database()` is intentionally NOT decorated (errors on startup should be fatal).

---

## Environment variables (.env — never committed)

```
DISCORD_TOKEN
ANTHROPIC_API_KEY
TURSO_DATABASE_URL
TURSO_AUTH_TOKEN
```

Set in Railway dashboard for production. Local `.env` file for development.

---

## All slash commands (22 total)

**Player commands (top-level):**
`/premonition`, `/myvisions`, `/myjournal`, `/help`, `/visionmenu`

**ST commands (top-level):**
`/setup`, `/settings`

**ST command groups:**
- `/thread` — `assign`, `status`, `end`, `pool`, `add`, `resetpool`
- `/vision` — `send`, `log`, `weights`, `resetweights`
- `/config` — `channel`, `cooldown`, `resetcooldown`, `clearsymbols`

---

## Vision types (9)

Standard Vision, Lucid Vision, Glitch Vision, Echo Vision, Resonance Bleed,
Nightmare Bleed, The Witness, The Warning, Retrocognition Surge

**Lucid Vision is special**: interactive `discord.ui.View` with choice buttons.
It is excluded from `/send_vision` (can't replicate interactivity in an ST send).
Only the original recipient can click the buttons (user ID checked in `_on_choice`).

---

## Database tables

| Table | Purpose |
|-------|---------|
| server_config | per-guild settings (roles, channel, night config) |
| vision_weights | per-guild probability weights for each vision type |
| player_cooldowns | tracks uses_this_night + last_reset_timestamp per player |
| vision_history | all generated visions (player and ST-sent) |
| vision_threads | active/historical motif threads per player |
| detected_symbols | recurring symbols identified by Claude from vision history |
| thread_pool | available motifs for auto-thread selection |

---

## Clan flavor text

`get_clan_flavor(interaction.user.roles)` in `utils.py` does a case-insensitive
substring match on role names against `CLAN_FLAVOR` in config.py. Returns one
random sentence to prepend to vision embeds, or None if no clan matched.
Supported clans: Toreador, Tremere, Malkavian, Salubri, Hecata, Banu Haqim.

---

## Deployment

Railway auto-deploys from the `main` branch on GitHub push.
Procfile: `worker: python main.py`
No build step needed — Railway detects `requirements.txt` automatically.
