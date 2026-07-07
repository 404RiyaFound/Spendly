# Spec: Registration

## Overview

Implement the `POST /register` flow so new users can actually create an account. Step 1 (Database Setup) already created the `users` table and the `GET /register` route already renders `register.html` with a form that posts to `/register`. This step wires that form up: validate input, hash the password, insert the user, and start a logged-in session. This is the second step in the Spendly roadmap and is a prerequisite for login (Step 3) and every logged-in route after it (profile, expenses).

## Depends on

- Step 1 — Database Setup (`database/db.py`: `get_db()`, `init_db()`, `users` table with `id`, `name`, `email`, `password_hash`, `created_at`).

## Routes

- `POST /register` – validate form input, create the user, start a session, redirect to profile/dashboard – public
- `GET /register` – already implemented, no changes needed

If validation fails (missing fields, invalid email, password too short, email already registered), re-render `register.html` with an `error` message and the previously entered values (except password) instead of redirecting.

## Database changes

None. `users` table already has every column needed (`name`, `email`, `password_hash`). No new tables, columns, or constraints required. New DB logic (an `insert_user()` / `get_user_by_email()` style function) belongs in `database/db.py`, not inline in `app.py`.

## Templates

- Create: none
- Modify: `templates/register.html` — repopulate `name`/`email` field values on validation error (e.g. `value="{{ name or '' }}"`) so the user doesn't retype everything

## Files to change

- `app.py` — implement `POST` handling on the existing `/register` route
- `database/db.py` — add parameterized functions for checking an existing email and inserting a new user
- `templates/register.html` — repopulate fields on error

## Files to create

None.

## New dependencies

No new dependencies. Use `werkzeug.security.generate_password_hash` (already a dependency) and Flask's built-in `session`.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only — never f-strings in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash` before storage; never store plaintext.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- DB logic (email lookup, insert) lives only in `database/db.py`; `app.py`'s route function should just: read form data, call the DB helper(s), render/redirect.
- Validate: `name`, `email`, `password` all present; email contains `@`; password is at least 8 characters (matches the placeholder text in `register.html`).
- Enforce uniqueness on email — check before insert (or catch the `UNIQUE` constraint failure) and show a friendly error, not a raw `sqlite3.IntegrityError`.
- On success, store the new user's id in `session` (e.g. `session["user_id"]`) so later steps (profile, logout) can rely on it.
- Use `abort()` for genuine HTTP errors, not for form validation — validation errors re-render the template with a message.

## Definition of done

- [ ] Submitting the register form with valid, unique details creates a row in `users` with a hashed (not plaintext) password
- [ ] After successful registration, the browser session contains the new user's id and the user is redirected away from `/register`
- [ ] Submitting with an email that already exists shows an error on the register page and does not create a duplicate row
- [ ] Submitting with a missing field (name, email, or password) shows an error and does not hit the database
- [ ] Submitting with a password under 8 characters shows an error and does not create a user
- [ ] Reloading `/register` after a failed submission still shows the previously entered name/email
- [ ] `python app.py` starts without errors and `/register` still renders on `GET`
