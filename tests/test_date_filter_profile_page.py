"""
Tests for the "Date Filter for Profile Page" feature (Step 6).

Spec: .claude/specs/06-date-filter-profile-page.md

These tests are written against the spec's intended behavior:
- GET /profile reads optional `start`/`end` query params (YYYY-MM-DD).
- Omitted/invalid params behave as if not provided (no errors).
- A reversed range (start > end) is silently swapped.
- Filtering flows through to summary stats, transaction list, and
  category breakdown.
- The filter form pre-fills with the submitted values.
- A filtered range with zero matches shows a zero-value summary and a
  "No transactions in this range" message instead of an empty table.
- /profile remains login-protected regardless of filter params.
"""

from werkzeug.security import generate_password_hash

from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)

# Expected all-time totals for the SEED_EXPENSES dataset defined in conftest:
#   2026-07-01  Food       100.00
#   2026-07-05  Transport  150.00
#   2026-07-10  Bills      300.00
#   2026-07-15  Food       250.00
#   2026-07-20  Shopping   500.00
ALL_TIME_TOTAL = "1300.00"
ALL_TIME_COUNT = 5
ALL_TIME_TOP_CATEGORY = "Shopping"

# start=2026-07-01, end=2026-07-15 (inclusive) -> rows 1-4
RANGE_TOTAL = "800.00"
RANGE_COUNT = 4
RANGE_TOP_CATEGORY = "Food"


class TestProfileRouteNoFilter:
    def test_no_query_params_shows_all_time_data(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        body = response.data.decode()
        assert f"₹{ALL_TIME_TOTAL}" in body, "Expected all-time total spent in response"
        assert f">{ALL_TIME_COUNT}<" in body, "Expected all-time transaction count in response"
        assert ALL_TIME_TOP_CATEGORY in body, "Expected all-time top category in response"

    def test_no_query_params_leaves_filter_inputs_empty(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode()
        assert 'name="start" value=""' in body, "start input should be pre-filled empty"
        assert 'name="end" value=""' in body, "end input should be pre-filled empty"


class TestProfileRouteRangeFilter:
    def test_start_and_end_restrict_to_range(self, auth_client):
        response = auth_client.get("/profile?start=2026-07-01&end=2026-07-15")
        assert response.status_code == 200
        body = response.data.decode()
        assert f"₹{RANGE_TOTAL}" in body
        assert f">{RANGE_COUNT}<" in body
        assert RANGE_TOP_CATEGORY in body
        # Expense outside the range should not appear in the transaction list.
        assert "New shoes" not in body
        assert "Groceries" in body

    def test_start_only_includes_on_and_after(self, auth_client):
        # dates >= 2026-07-10 -> Bills(300) + Food(250) + Shopping(500) = 1050.00, count 3
        response = auth_client.get("/profile?start=2026-07-10")
        assert response.status_code == 200
        body = response.data.decode()
        assert "₹1050.00" in body
        assert ">3<" in body
        assert "Groceries" not in body  # 2026-07-01, before start
        assert "Cab ride" not in body  # 2026-07-05, before start
        assert "New shoes" in body  # 2026-07-20, on/after start

    def test_end_only_includes_on_and_before(self, auth_client):
        # dates <= 2026-07-05 -> Food(100) + Transport(150) = 250.00, count 2
        response = auth_client.get("/profile?end=2026-07-05")
        assert response.status_code == 200
        body = response.data.decode()
        assert "₹250.00" in body
        assert ">2<" in body
        assert "Groceries" in body
        assert "Cab ride" in body
        assert "New shoes" not in body  # 2026-07-20, after end

    def test_reversed_range_is_swapped_and_matches_correct_order(self, auth_client):
        correct_order = auth_client.get("/profile?start=2026-07-01&end=2026-07-15")
        reversed_order = auth_client.get("/profile?start=2026-07-15&end=2026-07-01")

        assert correct_order.status_code == 200
        assert reversed_order.status_code == 200

        correct_body = correct_order.data.decode()
        reversed_body = reversed_order.data.decode()

        for expected in (f"₹{RANGE_TOTAL}", f">{RANGE_COUNT}<", RANGE_TOP_CATEGORY):
            assert expected in correct_body
            assert expected in reversed_body

    def test_malformed_start_date_is_ignored(self, auth_client):
        response = auth_client.get("/profile?start=not-a-date")
        assert response.status_code == 200
        body = response.data.decode()
        # Behaves as if start were omitted entirely -> all-time data.
        assert f"₹{ALL_TIME_TOTAL}" in body
        assert f">{ALL_TIME_COUNT}<" in body
        assert ALL_TIME_TOP_CATEGORY in body

    def test_malformed_end_date_is_ignored(self, auth_client):
        response = auth_client.get("/profile?end=also-not-a-date")
        assert response.status_code == 200
        body = response.data.decode()
        assert f"₹{ALL_TIME_TOTAL}" in body
        assert f">{ALL_TIME_COUNT}<" in body
        assert ALL_TIME_TOP_CATEGORY in body

    def test_malformed_start_does_not_raise_error(self, auth_client):
        # No 400/500 — malformed input must be silently ignored, not errored on.
        response = auth_client.get("/profile?start=not-a-date&end=2026-99-99")
        assert response.status_code == 200


class TestProfileRouteZeroMatch:
    def test_zero_match_range_shows_zero_summary(self, auth_client):
        response = auth_client.get("/profile?start=2026-08-01&end=2026-08-31")
        assert response.status_code == 200
        body = response.data.decode()
        assert "₹0.00" in body
        assert ">0<" in body
        assert "—" in body, "Expected em-dash placeholder for top category"

    def test_zero_match_range_shows_empty_state_message(self, auth_client):
        response = auth_client.get("/profile?start=2026-08-01&end=2026-08-31")
        body = response.data.decode()
        assert "No transactions in this range" in body

    def test_zero_match_range_does_not_render_transaction_rows(self, auth_client):
        response = auth_client.get("/profile?start=2026-08-01&end=2026-08-31")
        body = response.data.decode()
        # None of the seeded descriptions should be present.
        for description in ("Groceries", "Cab ride", "Electricity bill", "Dinner out", "New shoes"):
            assert description not in body


class TestProfileFilterFormPrefill:
    def test_form_inputs_prefilled_with_submitted_values(self, auth_client):
        response = auth_client.get("/profile?start=2026-07-01&end=2026-07-15")
        body = response.data.decode()
        assert 'name="start" value="2026-07-01"' in body
        assert 'name="end" value="2026-07-15"' in body

    def test_form_prefill_with_start_only(self, auth_client):
        response = auth_client.get("/profile?start=2026-07-10")
        body = response.data.decode()
        assert 'name="start" value="2026-07-10"' in body
        assert 'name="end" value=""' in body


class TestProfileAuthGuard:
    def test_unauthenticated_no_params_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_with_filter_params_redirects_to_login(self, client):
        response = client.get("/profile?start=2026-07-01&end=2026-07-15")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_never_leaks_seeded_data(self, client, seeded_user):
        response = client.get("/profile?start=2026-07-01")
        assert response.status_code == 302
        assert b"Groceries" not in response.data


class TestQueryFunctionsDateFilter:
    """DB-level tests for database/queries.py accepting start/end directly,
    independent of the Flask route."""

    def test_get_summary_stats_no_filter_is_all_time(self, seeded_user):
        stats = get_summary_stats(seeded_user)
        assert stats["transaction_count"] == ALL_TIME_COUNT
        assert float(stats["total_spent"]) == 1300.00
        assert stats["top_category"] == ALL_TIME_TOP_CATEGORY

    def test_get_summary_stats_with_range(self, seeded_user):
        stats = get_summary_stats(seeded_user, start="2026-07-01", end="2026-07-15")
        assert stats["transaction_count"] == RANGE_COUNT
        assert float(stats["total_spent"]) == 800.00
        assert stats["top_category"] == RANGE_TOP_CATEGORY

    def test_get_summary_stats_start_only(self, seeded_user):
        stats = get_summary_stats(seeded_user, start="2026-07-10")
        assert stats["transaction_count"] == 3
        assert float(stats["total_spent"]) == 1050.00

    def test_get_summary_stats_end_only(self, seeded_user):
        stats = get_summary_stats(seeded_user, end="2026-07-05")
        assert stats["transaction_count"] == 2
        assert float(stats["total_spent"]) == 250.00

    def test_get_summary_stats_zero_match_returns_zero_shape(self, seeded_user):
        stats = get_summary_stats(seeded_user, start="2026-08-01", end="2026-08-31")
        assert stats == {
            "total_spent": 0,
            "transaction_count": 0,
            "top_category": "—",
        }

    def test_get_recent_transactions_respects_range(self, seeded_user):
        transactions = get_recent_transactions(seeded_user, start="2026-07-01", end="2026-07-15")
        assert len(transactions) == RANGE_COUNT
        descriptions = {tx["description"] for tx in transactions}
        assert "New shoes" not in descriptions
        assert "Groceries" in descriptions

    def test_get_recent_transactions_zero_match_returns_empty_list(self, seeded_user):
        transactions = get_recent_transactions(seeded_user, start="2026-08-01", end="2026-08-31")
        assert transactions == []

    def test_get_category_breakdown_no_filter_percentages_sum_to_100(self, seeded_user):
        categories = get_category_breakdown(seeded_user)
        assert categories, "Expected non-empty breakdown for all-time data"
        percent_key = "percent" if "percent" in categories[0] else "pct"
        assert sum(c[percent_key] for c in categories) == 100

    def test_get_category_breakdown_with_range_percentages_sum_to_100(self, seeded_user):
        categories = get_category_breakdown(seeded_user, start="2026-07-01", end="2026-07-15")
        assert categories
        percent_key = "percent" if "percent" in categories[0] else "pct"
        assert sum(c[percent_key] for c in categories) == 100
        names = {c["name"] for c in categories}
        assert names == {"Food", "Transport", "Bills"}

    def test_get_category_breakdown_zero_match_returns_empty_list(self, seeded_user):
        categories = get_category_breakdown(seeded_user, start="2026-08-01", end="2026-08-31")
        assert categories == []

    def test_query_functions_are_scoped_to_the_requesting_user(self, seeded_user, test_db_path):
        # Insert a second, unrelated user with their own expense directly
        # against the isolated test DB (via a parameterized query), to
        # confirm filtering never leaks data across users.
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other User", "other@example.com", generate_password_hash("pw12345678")),
        )
        other_user_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (other_user_id, 999.00, "Food", "2026-07-01", "Someone else's lunch"),
        )
        conn.commit()
        conn.close()

        stats = get_summary_stats(seeded_user)
        assert float(stats["total_spent"]) == 1300.00, "Other user's expenses must not leak into totals"

        transactions = get_recent_transactions(seeded_user)
        descriptions = {tx["description"] for tx in transactions}
        assert "Someone else's lunch" not in descriptions
