# Stack Recipe — Polished Web Dashboard, Python Backend

A portable reference for the architecture used by the Zillah dashboard.
Pairs with **dashboard/mockups/DESIGN.md** (the visual design system).
Lift either or both into another project.

---

## 1 · When to pick this stack

This stack is good for:

- **One person, no JS framework expertise.** You write Python and HTML.
- **Backend already in Python**, or you'd rather keep it that way.
- **An app with a "compose / take action" surface**, not just "view data".
  (If it's mostly tables and forms, plain Django Admin is faster.)
- **A companion to a long-running process** — a Discord/Slack bot, a
  scheduled worker, a daemon — that you want to nudge from a UI without
  building an HTTP API between them.
- **You care about polish** — animations, focus management, nice
  dropdowns — but don't want to ship React.

This stack is **not great** for:
- Heavily interactive single-page experiences (drag-drop boards, real-time
  collaborative editing) — reach for React/Svelte instead.
- Apps where someone else will own the frontend — JS-framework people will
  find HTMX + Alpine unfamiliar.

---

## 2 · The stack at a glance

| Layer | Choice | Why |
|---|---|---|
| **Web framework** | FastAPI | Async, fast, Jinja & Form parsing built-in, OpenAPI for free if you want it later |
| **Templates** | Jinja2 | Familiar, partials work cleanly with HTMX |
| **CSS** | Tailwind (compiled) | Utility-first; no naming bikeshedding |
| **Client reactivity** | Alpine.js | Vue-like sprinkles, no build step, lives in HTML |
| **Server-driven swaps** | HTMX | Server returns HTML fragments; no JSON API to maintain |
| **Toasts** | Alpine store (Sonner-style) | One pattern, used by every action |
| **DB** | libsql / SQLite | Same DB the bot uses; no separate web DB |
| **Auth** | Discord OAuth (example) | App-specific; pattern works for any OAuth provider |
| **ASGI server** | Uvicorn | Standard FastAPI deploy target |
| **Deploy** | Railway (two processes) | `worker:` for the bot, `web:` for the dashboard, sharing env vars + DB |

**External JS, all vendored locally**: Alpine.js (~46KB), HTMX (~48KB), Tailwind compiled output (~15KB). Total: ~100KB. No CDN dependencies at runtime.

---

## 3 · Two-process architecture with a shared DB

The bot process and the web dashboard process can't easily talk to each
other over HTTP (different containers in Railway, different lifecycles).
They share a database, and they use the database as the queue:

```
┌─────────────────────┐         ┌─────────────────────┐
│   web (dashboard)   │         │   worker (bot)      │
│                     │         │                     │
│   FastAPI + Jinja   │         │   discord.py        │
│   uvicorn :8000     │         │   long-running      │
└──────────┬──────────┘         └──────────▲──────────┘
           │ writes                          │ polls
           │                                 │
           ▼                                 │
┌──────────────────────────────────────────────────────┐
│                  shared Turso / libsql DB             │
│                                                       │
│  · domain tables (config, history, threads, …)        │
│  · vision_drafts        — composed in web, lives here │
│  · vision_outbox        — written by web, drained by  │
│                           bot, each row marked sent / │
│                           failed                      │
└──────────────────────────────────────────────────────┘
```

**The outbox pattern** is the load-bearing piece here. Any time the web
process needs the bot process to *do* something irreversible (send a
Discord message, run a slow job, call a third-party API), it writes a row
to an outbox table and returns success immediately. The bot's polling
worker drains the table and does the work.

Why it's worth knowing:
- **No HTTP between processes** — they only talk through the DB
- **Survives crashes** — restart the bot and pending work resumes
- **Trivially testable** — write outbox rows in tests, no mocks needed
- **Failure visible** — a row marked `failed` with an error string is
  easy to inspect later

See `db.py` (`enqueue_inflict`, `drain_outbox_pending`,
`mark_outbox_sent`, `mark_outbox_failed`) and `outbox_worker.py`.

---

## 4 · File structure

```
project_root/
  main.py                    # bot entrypoint
  bot.py                     # bot wiring, spawns outbox_worker.run
  outbox_worker.py           # asyncio polling task — drains the outbox
  db.py                      # shared DB helpers (bot + dashboard)
  config.py                  # shared constants
  utils.py                   # shared helpers

  Procfile                   # worker: + web: lines
  requirements.txt           # all Python deps (both processes)

  dashboard/
    __init__.py
    app.py                   # FastAPI entrypoint, lifespan, middleware
    config.py                # dashboard-only env vars
    auth.py                  # session + permission helpers
    discord_api.py           # OAuth + member-lookup httpx wrappers
    data.py                  # data layer — wraps db.py for templates

    routes/
      __init__.py
      auth.py                # /auth/login, /auth/callback, /auth/logout
      kindred.py             # GET pages
      drafts.py              # POST/DELETE — HTMX targets

    templates/
      base.html              # layout, loads vendored JS/CSS
      _header.html
      _footer.html
      _drafts_list.html      # partial reused for initial render AND HTMX swap
      kindred_list.html
      editor.html
      login.html
      no_access.html

    static/
      css/
        codex.css            # design tokens + components (committed)
        tailwind.css         # compiled from tailwind.input.css (committed)
      js/
        codex.js             # Alpine bootstrap + components (committed)
      vendor/
        alpine.min.js        # vendored — no CDN at runtime
        htmx.min.js          # vendored

    package.json             # for tailwindcss CLI + Alpine + HTMX (devDeps)
    tailwind.config.js
    tailwind.input.css       # @tailwind base/components/utilities
    .gitignore               # node_modules only
```

---

## 5 · The patterns worth keeping

### 5.1 — Alpine for client state, HTMX for server roundtrips

A clean split:

- **Alpine** owns things that don't need the server: open/closed,
  selected chip, char count, modal visibility, draft loaded into the
  editor, keyboard shortcuts.
- **HTMX** owns things that change the server: Save Draft, Delete,
  Inflict (write to outbox), Refresh the drafts list.

Buttons can do both. Example:

```html
<button
  class="btn-ghost"
  hx-post="/g/{guild.id}/kindred/{user_id}/drafts"
  hx-include="[name='vision_type'], [name='body']"
  hx-target="#drafts-list"
  hx-swap="outerHTML"
  @click="dirty = false">  <!-- Alpine fires too -->
  Save Draft
</button>
```

### 5.2 — Server-rendered partials reused for initial paint AND HTMX swaps

The drafts list is rendered by `_drafts_list.html`. The first time you
load the editor page, it's included via `{% include %}`. When you click
Save Draft, the server returns the **same template** rendered with the
updated list, and HTMX swaps the `<ul>` in place.

**One source of truth.** Never write `JSON.parse()` for something the
server already knows how to render.

### 5.3 — Toast as a response header

Every HTMX-targeted POST/DELETE returns an `X-Codex-Toast: ...` header.
A four-line client-side listener turns it into a toast:

```js
document.addEventListener('htmx:afterRequest', (e) => {
  const msg = e.detail.xhr.getResponseHeader('X-Codex-Toast');
  if (msg) Alpine.store('toast').show(msg);
});
```

Why this is good:
- **Wire format stays trivial** — no envelope JSON, no `{ok: true, message: ...}`
- **The response body is still HTML** (the partial to swap)
- **Toast is decoupled** — any endpoint can opt in by adding the header

### 5.4 — Sessions over signed cookies (no DB session table)

Starlette's `SessionMiddleware` signs the session payload with a secret
key. The user's id, the list of guilds/projects they have access to, and
the OAuth access token live in the cookie itself. No DB writes per
request.

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=DASHBOARD_SESSION_SECRET,
    session_cookie="zillah_session",
    max_age=60 * 60 * 24 * 14,  # 14 days
    same_site="lax",
    https_only=os.getenv("RAILWAY_ENVIRONMENT") is not None,
)
```

### 5.5 — Permission as a session-cached list

At OAuth callback, cross-reference the user's guilds (from Discord)
against your DB's configured-guilds list, and against per-guild role
checks. Store the resulting `accessible_guilds = [...]` in the session.

Every protected route checks the URL's `guild_id` against the session
list. **One Discord round-trip per login**, not per request.

### 5.6 — Vendor your JS dependencies

`cdn.tailwindcss.com` is for prototypes only. In production, ship:

- Compiled Tailwind CSS (`tailwindcss -i input.css -o static/css/tailwind.css --minify`)
- Vendored Alpine.js (`cp node_modules/alpinejs/dist/cdn.min.js static/vendor/`)
- Vendored HTMX (`cp node_modules/htmx.org/dist/htmx.min.js static/vendor/`)

Commit the output. Your deploy doesn't need npm. Your runtime doesn't
need internet to load the JS. The `npm run build` step is the only
moment a build chain exists.

### 5.7 — Dev preview gate

Setting `DASHBOARD_DEV_PREVIEW=1` enables a `/_dev/seed` route that
injects a mock session. Guarded so it can never accidentally ship to
production. Lets you run the dashboard locally without going through
real OAuth.

```python
if os.getenv("DASHBOARD_DEV_PREVIEW") == "1":
    @app.get("/_dev/seed")
    async def _dev_seed(request: Request):
        request.session["user"] = {"id": "999", "username": "tester"}
        request.session["guilds"] = [{"id": "100", "name": "Test Domain"}]
        return RedirectResponse(url="/", status_code=307)
```

---

## 6 · Setup, from blank to running

```bash
# 1. Python deps (both processes share)
cat > requirements.txt <<'EOF'
fastapi>=0.110
uvicorn[standard]>=0.27
jinja2>=3.1
itsdangerous>=2.1
httpx>=0.27
python-multipart>=0.0.9
python-dotenv>=1.0
libsql-experimental
EOF
pip install -r requirements.txt

# 2. JS build chain for static assets
cd dashboard
cat > package.json <<'EOF'
{
  "private": true,
  "scripts": {
    "build": "tailwindcss -i ./tailwind.input.css -o ./static/css/tailwind.css --minify && cp node_modules/alpinejs/dist/cdn.min.js static/vendor/alpine.min.js && cp node_modules/htmx.org/dist/htmx.min.js static/vendor/htmx.min.js"
  },
  "devDependencies": {
    "alpinejs": "^3.14",
    "htmx.org": "^1.9",
    "tailwindcss": "^3.4"
  }
}
EOF
mkdir -p static/vendor
npm install
npm run build
cd ..

# 3. Procfile (Railway)
cat > Procfile <<'EOF'
worker: python main.py
web: uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT
EOF

# 4. Run locally
DASHBOARD_DEV_PREVIEW=1 \
TURSO_DATABASE_URL=local.db \
TURSO_AUTH_TOKEN=x \
uvicorn dashboard.app:app --reload --port 8000
```

---

## 7 · Bill of materials

### Python (requirements.txt)

```
fastapi>=0.110              # web framework
uvicorn[standard]>=0.27     # ASGI server
jinja2>=3.1                 # templates
itsdangerous>=2.1           # session cookie signing (Starlette dependency)
httpx>=0.27                 # OAuth API calls
python-multipart>=0.0.9     # FastAPI Form parsing
python-dotenv>=1.0          # .env loading

libsql-experimental         # libsql / SQLite client
# OR: psycopg2-binary, sqlalchemy, etc. — pattern is DB-agnostic
```

### JS (dashboard/package.json devDependencies)

```
alpinejs ^3.14
htmx.org ^1.9
tailwindcss ^3.4
```

### Fonts (Google Fonts)

```
Cinzel              — display headings, small-caps labels
Cormorant Garamond  — decorative serif (names, subtitles)
EB Garamond         — body prose
Inter               — UI chrome
```

(Plus optional: `Homemade Apple` for handwritten marginalia.)

---

## 8 · Design layer

The visual half of the system — palette, type, surfaces, atmosphere
techniques, restraint rules, microcopy voice — lives separately in
**`dashboard/mockups/DESIGN.md`**. That doc is portable on its own
even if you don't use this stack.

Quick summary of how the two relate:

- **STACK.md (this file)** — architecture, files, patterns, deps
- **DESIGN.md** — colors, fonts, gilded surfaces, drop caps, candlelight
  flicker, voice rules ("Inflict" not "Send")

You can lift only one for a project that needs only that half, or both
for a project that needs both.

---

## 9 · What's deliberately not here

Things this stack does **not** give you out of the box, that you may need
to add for your project:

- **Real-time** (server-sent events, websockets) — HTMX has `hx-ext="sse"`
  and FastAPI supports SSE natively if you need a streaming editor or a
  live progress UI
- **File uploads** — straightforward in FastAPI, but no example here
- **Pagination** — your responsibility; HTMX makes infinite scroll easy
- **Email** — outside scope; use `aiosmtplib` or a transactional service
- **Background scheduling** beyond the outbox poller — for cron-style
  jobs, reach for APScheduler or just an `asyncio.sleep` loop in the
  worker

---

## 10 · TL;DR

```
Python + FastAPI + Jinja  for the server
Tailwind + Alpine + HTMX  for the client (all vendored)
libsql / SQLite           for storage
Outbox table              for cross-process commands
X-Codex-Toast header      for HTMX success feedback
DASHBOARD_DEV_PREVIEW=1   for local development without OAuth
```

That's the whole recipe.
