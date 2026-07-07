# Spec: Login and Logout

## Overview

Implement the `POST /login` flow and the `GET /logout` route so registered users can actually sign in and out of Spendly. Step 1 (Database Setup) created the `users` table and Step 2 (Registration) wired up account creation and starts a session on signup. `GET /login` already renders `login.html` with a form posting to `/login`, and `GET /logout` is currently a stub string. This step verifies credentials against the stored password hash, starts a session on success, and clears the session on logout. This is the third step in the Spendly roadmap and is a prerequisite for `/profile` (Step 4) and every other logged-in route after it.

## Depends on

- Step 1 — Database Setup (`database/db.py`: `get_db()`, `init_db()`, `users` table with `id`, `name`, `email`, `password_hash`, `created_at`).
- Step 2 — Registration (`get_user_by_email()` helper exists; `session["user_id"]` convention established on signup).

## Routes

- `POST /login` — validate credentials against the `users` table, start a session, redirect to profile — public
- `GET /login` — already implemented, no changes needed
- `GET /logout` — clear the session and redirect to the landing page — logged-in (safe to hit while logged out; just redirects)

If login validation fails (missing fields, unknown email, wrong password), re-render `login.html` with an `error` message instead of redirecting. Do not reveal whether the email or the password was the wrong part — use one generic error message for both cases.

## Database changes

None. The `users` table already has every column needed (`email`, `password_hash`). `get_user_by_email()` currently only selects `id` — it needs to also return `password_hash` (and `name`, since Step 4/profile will want it) so `app.py` can verify the password. This is a change to an existing function's query, not a new table/column.

## Templates

- Create: none
- Modify: `templates/login.html` — repopulate the `email` field value on validation error (e.g. `value="{{ email or '' }}"`), matching the pattern already used in `register.html`

## Files to change

- `app.py` — implement `POST` handling on the existing `/login` route; implement `/logout` to clear the session and redirect
- `database/db.py` — update `get_user_by_email()` to also return `password_hash` and `name` (needed to verify login and to populate the session)
- `templates/login.html` — repopulate the email field on error

## Files to create

None.

## New dependencies

No new dependencies. Use `werkzeug.security.check_password_hash` (already available alongside `generate_password_hash`) and Flask's built-in `session`.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only — never f-strings in SQL.
- Passwords hashed with `werkzeug` — use `check_password_hash()` to verify; never compare plaintext passwords.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- DB logic (looking up the user by email) lives only in `database/db.py`; `app.py`'s route function should just: read form data, call the DB helper, verify the password, set/clear session, render/redirect.
- Validate: `email` and `password` are both present before querying the database.
- Use a single generic error message ("Invalid email or password.") whether the email doesn't exist or the password is wrong — don't leak which one was incorrect.
- On successful login, store the user's id in `session["user_id"]`.
- On logout, remove `user_id` from `session` (e.g. `session.pop("user_id", None)`) and redirect to the landing page.
- Use `abort()` for genuine HTTP errors, not for form validation — validation errors re-render the template with a message.

## Definition of done

- [ ] Submitting the login form with a registered email and correct password redirects away from `/login` and the session contains that user's id
- [ ] Submitting the login form with a correct email but wrong password shows a generic "Invalid email or password." error and does not set the session
- [ ] Submitting the login form with an email that doesn't exist shows the same generic error and does not set the session
- [ ] Submitting the login form with a missing email or password shows an error and does not hit the database
- [ ] Reloading `/login` after a failed submission still shows the previously entered email (not password)
- [ ] Visiting `/logout` while logged in clears the session and redirects to the landing page
- [ ] Visiting `/logout` while already logged out does not error, and redirects to the landing page
- [ ] `python app.py` starts without errors and `/login` still renders on `GET`
