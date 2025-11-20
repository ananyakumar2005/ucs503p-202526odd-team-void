## Quick orientation

This repo is a small Flask webapp (single-process) for campus bartering. Key files:

- `app.py` — main Flask application and route handlers. Handles authentication (Flask-Login), page routing, and form handling.
- `database.py` — lightweight SQLite helper. Exposes `get_db_connection()` and runs `init_db()` on import to create `campustrade.db` in the repo working directory.
- `templates/` — Jinja2 templates used by the routes (e.g. `index.html`, `login.html`, `register.html`, `trade_offers.html`).

Important runtime notes:

- The app reads `SECRET_KEY` from the environment; if missing it falls back to a dev key and prints a warning. Set `SECRET_KEY` for production.
- The app creates a default `admin` user on startup if missing.
- The DB file is `campustrade.db` and lives in the repository working directory (no migrations or ORM).

## Architecture and data flow (concise)

- Web requests hit routes in `app.py`. Most read/write operations use raw SQL via `get_db_connection()` from `database.py`.
- Authentication: `Flask-Login` with a `User` wrapper class and `load_user` using a SQL lookup by `id`.
- Barters/Requests/TradeOffers are plain tables operated on with SQL statements in `app.py` and `database.py`.

## Developer workflows & quick commands (PowerShell)

- Create a virtual env and install deps:

  $ python -m venv venv
  $ .\venv\Scripts\Activate.ps1
  $ pip install -r requirements.txt

- Run locally (port 5000):

  # set secret in current PowerShell session
  $env:SECRET_KEY = 'your-secret-here'
  $ python app.py

Notes: the app uses `app.run(host="0.0.0.0", port=PORT)` and reads `PORT` from the environment for hosting providers (e.g. Render).

## Project-specific conventions & patterns

- Raw SQL is used everywhere (no ORM). Use parameterized queries (see existing `?` usage) to avoid SQL injection.
- DB initialization happens on import (`init_db()` in `database.py`) and again in `app.py` via `initialize_app()` — be mindful of duplicate calls when refactoring.
- Templates expect variables named in `app.py` (e.g. `barters`, `requests`, `trade_offers`, `username`, `trade_offers_count`). Keep those names when changing route logic.

## Integration & deployment cues

- Environment variables used: `SECRET_KEY`, optional `PORT`.
- The SQLite file is created in the current working directory — on hosted platforms you may need to ensure write permission or move to a persistent storage location.

## Examples (copy/paste patterns)

- Query barters with usernames (JOIN):

  conn.execute("""
  SELECT b.*, u.username
  FROM barters b
  JOIN users u ON b.user_id = u.id
  WHERE b.is_active = 1
  ORDER BY b.created_at DESC
  """)

- Insert a trade offer (use parameterized args):

  conn.execute(
      'INSERT INTO trade_offers (barter_id, user_id, barter_item, barter_owner, offerer_name, offerer_mobile, item_description) VALUES (?, ?, ?, ?, ?, ?, ?)',
      (barter_id, current_user.id, barter['item'], barter['username'], name, mobile, item_description)
  )

## What to watch for / known quirks

- `init_db()` is executed when `database.py` is imported. Be careful when importing `database` in tests or one-off scripts to avoid side-effects.
- `app.run()` sets `debug=False` in `__main__`. To enable the debugger locally, change the `debug` flag or run via Flask CLI and set `FLASK_ENV=development`.
- No automated tests or CI configured in the repo currently.

---
If any of this is inaccurate or you want additional sections (tests, CI setup, or a sample dev script), tell me which area to expand and I will iterate.
