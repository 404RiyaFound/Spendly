from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if user is None:
        return None

    created_at = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")

    return {
        "name": user["name"],
        "email": user["email"],
        "member_since": created_at.strftime("%B %Y"),
    }


def _date_range_clause(user_id, start, end):
    conditions = ["user_id = ?"]
    params = [user_id]
    if start:
        conditions.append("date >= ?")
        params.append(start)
    if end:
        conditions.append("date <= ?")
        params.append(end)
    return " AND ".join(conditions), params


def get_recent_transactions(user_id, limit=10, start=None, end=None):
    where_clause, params = _date_range_clause(user_id, start, end)
    params.append(limit)

    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount FROM expenses "
        f"WHERE {where_clause} ORDER BY date DESC LIMIT ?",
        params,
    ).fetchall()
    conn.close()

    transactions = []
    for row in rows:
        display_date = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y")
        transactions.append(
            {
                "date": display_date,
                "description": row["description"],
                "category": row["category"],
                "amount": float(row["amount"]),
            }
        )

    return transactions


def get_summary_stats(user_id, start=None, end=None):
    where_clause, params = _date_range_clause(user_id, start, end)

    conn = get_db()

    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total_spent, "
        f"COUNT(*) AS transaction_count FROM expenses WHERE {where_clause}",
        params,
    ).fetchone()

    top_category_row = conn.execute(
        "SELECT category, SUM(amount) AS category_total FROM expenses "
        f"WHERE {where_clause} GROUP BY category "
        "ORDER BY category_total DESC, category ASC LIMIT 1",
        params,
    ).fetchone()

    conn.close()

    if totals["transaction_count"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": totals["total_spent"],
        "transaction_count": totals["transaction_count"],
        "top_category": top_category_row["category"],
    }


def get_category_breakdown(user_id, start=None, end=None):
    where_clause, params = _date_range_clause(user_id, start, end)

    conn = get_db()
    rows = conn.execute(
        f"""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE {where_clause}
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    ).fetchall()
    conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)

    categories = []
    for row in rows:
        total = row["total"]
        percent = round((total / grand_total) * 100) if grand_total else 0
        categories.append({"name": row["category"], "total": float(total), "percent": percent})

    remainder = 100 - sum(category["percent"] for category in categories)
    if remainder != 0:
        largest = max(categories, key=lambda category: category["total"])
        largest["percent"] += remainder

    return categories
