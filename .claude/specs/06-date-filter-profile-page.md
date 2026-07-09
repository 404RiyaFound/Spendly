# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the `/profile` page so users can narrow their summary stats, transaction list, and category breakdown to a specific time window instead of always seeing all-time totals. Step 5 connected the profile page to live data via `database/queries.py`; this step extends those same query functions to accept an optional date range and adds a small filter form to `profile.html` that resubmits `GET /profile` with `start`/`end` query parameters. This is a pure filtering feature — no new tables, no new routes, no write operations.

## Depends on
- Step 1: Database setup (`expenses.date` column, `YYYY-MM-DD` format)
- Step 3: Login/Logout (`session["user_id"]`)
- Step 4: Profile page static UI
- Step 5: Backend connection (`database/queries.py` — `get_summary_stats`, `get_recent_transactions`, `get_category_breakdown`)

## Routes
No new routes. The existing `GET /profile` route is modified to read two optional query string parameters:
- `start` — `YYYY-MM-DD`, inclusive lower bound
- `end` — `YYYY-MM-DD`, inclusive upper bound

Both are optional and independent — a user can supply just `start`, just `end`, both, or neither (neither = all-time, current behavior). Invalid or malformed date strings are ignored (treated as not provided), not errored on.

## Database changes
No database changes. `expenses.date` is already stored as `YYYY-MM-DD` text, which sorts and compares correctly with SQL `BETWEEN`/`>=`/`<=` on the same format.

## Templates
- **Modify**: `templates/profile.html`
  - Add a filter form above the summary stats: two `<input type="date">` fields (`start`, `end`) plus a "Filter" submit button and a "Clear" link back to `/profile` with no query params.
  - Form uses `method="get"` and posts to `url_for('profile')` — no new route needed.
  - Pre-fill the `start`/`end` inputs with the currently active values (via `value="{{ request.args.get('start', '') }}"` etc.) so the filter persists visually after submit.
  - If a filter is active and the transaction list is empty, show a short "No transactions in this range" message instead of an empty table body.

## Files to change
- `app.py` — read `start`/`end` from `request.args` in the `profile()` view, validate/parse them, pass them through to the three query helpers, and pass the raw values back to the template for pre-filling the form
- `database/queries.py` — add optional `start=None, end=None` parameters to `get_summary_stats`, `get_recent_transactions`, `get_category_breakdown`; build the `WHERE` clause conditionally so omitted bounds don't filter
- `templates/profile.html` — add the filter form and empty-state message

## Files to create
None.

## New dependencies
No new dependencies. Use `datetime.strptime` (already imported in `database/queries.py`) to validate incoming date strings.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format date values into SQL, including the conditional `WHERE` clause
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Date parsing/validation for `start`/`end` happens in `app.py` (the route boundary), not inside `database/queries.py` — the query functions should assume they receive either `None` or a valid `YYYY-MM-DD` string
- If `start` is provided and `end` is provided and `start > end`, swap them rather than erroring, so the filter still returns a sensible result
- If a date string fails to parse, silently treat it as absent (`None`) rather than raising or showing an error to the user
- `get_summary_stats` must still return the zero-value shape (`{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`) when no expenses fall in the filtered range
- `get_category_breakdown` must still return `[]` when no expenses fall in the filtered range, and `pct`/`percent` values must still sum to 100 when there are results
- Currency must always display as ₹ — never £ or $

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data, identical to Step 5 behavior
- [ ] Visiting `/profile?start=2026-07-01&end=2026-07-15` shows summary stats, transactions, and category breakdown restricted to that range only
- [ ] Visiting `/profile?start=2026-07-01` (no `end`) includes all expenses on or after that date
- [ ] Visiting `/profile?end=2026-07-15` (no `start`) includes all expenses on or before that date
- [ ] Visiting `/profile?start=2026-07-15&end=2026-07-01` (reversed range) returns the same result as the correctly ordered range
- [ ] Visiting `/profile?start=not-a-date` does not error and behaves as if `start` were omitted
- [ ] A filtered range with zero matching expenses shows ₹0.00 total spent, 0 transactions, "—" top category, and a "No transactions in this range" message instead of an empty table
- [ ] The filter form's `start`/`end` inputs are pre-filled with the values from the current query string after submitting
- [ ] A "Clear" link returns to `/profile` with no query params and restores all-time data
- [ ] `python app.py` starts without errors and `/profile` still requires login
