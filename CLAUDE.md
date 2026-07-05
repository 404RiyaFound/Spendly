# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

"Spendly" is a Flask expense tracker built incrementally as a step-by-step learning project. Route handlers and `database/db.py` are scaffolded with comments describing what each step should implement (e.g. `# Placeholder routes — students will implement these`, `# Students will write this file in Step 1 — Database Setup`). When asked to implement a route or the database layer, check the existing comments/docstrings in that file first — they describe the expected step and scope; don't jump ahead and implement later steps unless asked.

## Commands

Activate the virtualenv before running anything (already created at `venv/`):

```
source venv/bin/activate
```

Run the app (serves on port 5001):

```
python app.py
```

Run tests:

```
pytest
```

Install/update dependencies:

```
pip install -r requirements.txt
```

## Architecture

- `app.py` — single Flask application with all routes defined directly on `app` (no blueprints). Templates are rendered with `render_template`; routes not yet implemented return a plain placeholder string naming the step that will implement them.
- `database/db.py` — intended to hold `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (creates tables with `CREATE TABLE IF NOT EXISTS`), and `seed_db()` (sample dev data). Currently empty — do not assume any helpers exist until the step that implements them.
- `templates/` — Jinja2 templates. `base.html` is the shared layout (nav, footer, font/CSS/JS includes); page templates extend it via `{% block title %}`, `{% block content %}`, `{% block head %}`, `{% block scripts %}`. Auth forms (`login.html`, `register.html`) post directly to `/login` and `/register` and expect an `error` template variable for validation feedback.
- `static/css/landing.css` — single stylesheet shared across all pages (landing, auth, terms, privacy).
- `static/js/main.js` — currently empty; JS is added incrementally alongside features.
- SQLite database file is `expense_tracker.db` (gitignored), created via `database/db.py` once implemented.

## Where things belong

- New routes → `app.py` only, no blueprints.
- DB logic → `database/db.py` only, never inline in routes.
- New pages → new `.html` file extending `base.html`.
- Page-specific styles → a new `.css` file, not inline `<style>` tags.

## Tech constraints

- Flask only — no FastAPI, Django, or other web frameworks.
- SQLite only — no PostgreSQL, no SQLAlchemy ORM, no external DB.
- Vanilla JS only — no React, no jQuery, no npm packages.
- No new pip packages — work within `requirements.txt` as-is unless explicitly told otherwise.
- Python 3.10+ assumed — f-strings and `match` statements are fine.
- Currency is INR, not USD — format amounts with ₹, not $, in templates, seed data, and any currency defaults.

## Code style

- Python: PEP 8, snake_case for all variables and functions.
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs.
- Route functions: one responsibility only — fetch data, render template, done.
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL.
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`.

## Route status

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET /register` | Implemented — renders `register.html` |
| `GET /login` | Implemented — renders `login.html` |
| `GET /logout` | Stub — Step 3 |
| `GET /profile` | Stub — Step 4 |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

## Warnings and things to avoid

- Never leave a raw string return on a stub route once its step is implemented — always render a template.
- Never hardcode URLs in templates — always use `url_for()`.
- Never put DB logic in route functions — it belongs in `database/db.py`.
- Never install new packages mid-feature without flagging it — keep `requirements.txt` in sync.
- Never use JS frameworks — the frontend is intentionally vanilla.
- SQLite foreign keys are off by default — `get_db()` must run `PRAGMA foreign_keys = ON` on every connection.
- The app runs on port 5001, not the Flask default 5000 — don't change this.
