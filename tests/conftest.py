"""
Shared pytest fixtures for the Spendly test suite.

Key design note
----------------
`database/db.py` connects with a hardcoded `DB_PATH` (a file in the project
root) rather than reading from Flask's `app.config`. To keep tests fully
isolated from the real `expense_tracker.db` (and from each other), every
fixture here monkeypatches `database.db.DB_PATH` to a fresh temp file
*before* any table is created. Because `get_db()` looks up the `DB_PATH`
module global at call time (not at import time), patching the module
attribute is sufficient to redirect every subsequent `get_db()` call --
including ones made indirectly through `database/queries.py` and `app.py`.

We also patch `DB_PATH` once at module import time, before `app` is
imported, because `app.py` calls `init_db()` / `seed_db()` at import time
(module-level `with app.app_context(): ...`). Without this, simply
importing `app` during test collection would create/seed the *real*
`expense_tracker.db` file in the project root.
"""

import os
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database.db as db  # noqa: E402

# Redirect DB_PATH to a throwaway temp file *before* importing app, so the
# module-level init_db()/seed_db() call inside app.py never touches the
# real project database.
_bootstrap_fd, _bootstrap_path = tempfile.mkstemp(suffix=".db")
os.close(_bootstrap_fd)
db.DB_PATH = _bootstrap_path

from app import app as flask_app  # noqa: E402
from database.db import get_db, init_db  # noqa: E402


@pytest.fixture
def test_db_path(tmp_path, monkeypatch):
    """Point every get_db() call at a fresh, isolated SQLite file for the
    duration of a single test, and create the schema in it."""
    db_file = tmp_path / "test_spendly.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_file))
    init_db()
    yield str(db_file)


@pytest.fixture
def app(test_db_path):
    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
        }
    )
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def create_user(name="Filter User", email="filteruser@example.com", password="testpass123"):
    """Insert a user directly via a parameterized query and return its id."""
    from werkzeug.security import generate_password_hash

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def add_expense(user_id, amount, category, expense_date, description=""):
    """Insert an expense directly via a parameterized query."""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


# Deterministic dataset used across the date-filter tests. Chosen so that
# every filtered subset used in the tests has an unambiguous "top category"
# (no ties), which keeps assertions unambiguous without relying on any
# particular implementation detail for tie-breaking.
SEED_EXPENSES = [
    # amount, category, date, description
    (100.00, "Food", "2026-07-01", "Groceries"),
    (150.00, "Transport", "2026-07-05", "Cab ride"),
    (300.00, "Bills", "2026-07-10", "Electricity bill"),
    (250.00, "Food", "2026-07-15", "Dinner out"),
    (500.00, "Shopping", "2026-07-20", "New shoes"),
]


@pytest.fixture
def seeded_user(test_db_path):
    """Create a single user with a deterministic, dated set of expenses.

    All-time totals for this dataset:
    - total_spent = 1300.00, transaction_count = 5, top_category = "Shopping"
    """
    user_id = create_user()
    for amount, category, expense_date, description in SEED_EXPENSES:
        add_expense(user_id, amount, category, expense_date, description)
    return user_id


@pytest.fixture
def auth_client(client, seeded_user):
    """A test client logged in (via session) as the seeded user."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user
        sess["user_name"] = "Filter User"
    return client
