from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import random
import sqlite3
from typing import Any, Dict, Generator, List, Optional

from app.config import settings


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    target_path = Path(db_path or settings.db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database transactions."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _get_expenses_table_name(cursor: sqlite3.Cursor) -> str:
    """Return 'montly_expenses' if present, otherwise 'category_expenses'."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='montly_expenses';")
    if cursor.fetchone():
        return "montly_expenses"
    return "category_expenses"


def create_tables(conn: sqlite3.Connection) -> None:
    """Create database tables for API classes if they don't already exist."""
    cursor = conn.cursor()

    # 1. Metric Summary Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS "metric_summary" (
            "id" INTEGER,
            "monthly_budget" REAL NOT NULL,
            "savings_target" REAL NOT NULL,
            "updated_at" TEXT NOT NULL DEFAULT (DATETIME('now')),
            "running_month" DATETIME,
            PRIMARY KEY("id" AUTOINCREMENT)
        );
        """
    )

    # 2. Monthly Expenses Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS "montly_expenses" (
            "id" INTEGER,
            "name" TEXT NOT NULL,
            "amount" REAL,
            "budget" REAL NOT NULL,
            "percentage" NUMERIC NOT NULL,
            "color" TEXT,
            "icon" TEXT NOT NULL,
            "expense_date" DATETIME,
            PRIMARY KEY("id" AUTOINCREMENT)
        );
        """
    )


    # 4. Transactions Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            icon TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now'))
        );
        """
    )


def seed_default_data(conn: sqlite3.Connection, force: bool = False) -> None:
    """Populate database with default initial data if tables are empty."""
    cursor = conn.cursor()

    # Seed Metric Summary
    cursor.execute("SELECT COUNT(*) FROM metric_summary;")
    if cursor.fetchone()[0] == 0 or force:
        now = datetime.now()
        if force:
            cursor.execute("DELETE FROM metric_summary;")

        cursor.execute(
            """
            INSERT INTO "metric_summary" (
                monthly_budget, savings_target, updated_at, running_month
            ) VALUES (?, ?, DATETIME('now'), ?);
            """,
            (
                3500.00,
                800.00,
                now.strftime("%Y-%m-%d 00:00:00"),
            ),
        )

    # Seed Monthly Expenses
    tbl = _get_expenses_table_name(cursor)
    cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
    if cursor.fetchone()[0] == 0 or force:
        if force:
            cursor.execute(f"DELETE FROM {tbl};")
        categories = [
            ("Housing & Utilities", 850.00, 900.00, 45.3, "#6A8D73", "home", now.strftime("%Y-%m-01 00:00:00")),
            ("Groceries & Food", 420.50, 550.00, 22.4, "#F0A868", "shopping-cart", now.strftime("%Y-%m-05 12:00:00")),
            ("Dining & Coffee", 195.30, 250.00, 10.4, "#FFE8C2", "coffee", now.strftime("%Y-%m-10 09:30:00")),
            ("Transportation", 165.20, 200.00, 8.8, "#E4FFE1", "car", now.strftime("%Y-%m-12 08:15:00")),
            ("Entertainment", 114.40, 150.00, 6.1, "#F4FDD9", "film", now.strftime("%Y-%m-25 18:00:00")),
            ("Personal & Tech", 130.00, 200.00, 6.9, "#94A89A", "smartphone", now.strftime("%Y-%m-28 14:00:00")),
        ]
        total = sum(c[1] for c in categories)
        cursor.execute(f"PRAGMA table_info({tbl});")
        has_expense_date = "expense_date" in [r[1] for r in cursor.fetchall()]

        if has_expense_date:
            cursor.executemany(
                f"""
                INSERT INTO {tbl} (name, amount, budget, percentage, color, icon, expense_date)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        c[0],
                        c[1],
                        c[2],
                        round((c[1] / total) * 100, 1),
                        c[4],
                        c[5],
                        c[6],
                    )
                    for c in categories
                ],
            )
        else:
            cursor.executemany(
                f"""
                INSERT INTO {tbl} (name, amount, budget, percentage, color, icon)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        c[0],
                        c[1],
                        c[2],
                        round((c[1] / total) * 100, 1),
                        c[4],
                        c[5],
                    )
                    for c in categories
                ],
            )


    # Seed Transactions
    cursor.execute("SELECT COUNT(*) FROM transactions;")
    if cursor.fetchone()[0] == 0 or force:
        if force:
            cursor.execute("DELETE FROM transactions;")
        transactions = [
            (
                "tx-101",
                "Whole Foods Market",
                "Groceries & Food",
                64.20,
                "Today, 3:45 PM",
                "Apple Pay",
                "shopping-cart",
            ),
            (
                "tx-102",
                "Metro Transit Monthly Pass",
                "Transportation",
                45.00,
                "Today, 8:15 AM",
                "Debit Card",
                "car",
            ),
            (
                "tx-103",
                "Starbucks Coffee",
                "Dining & Coffee",
                7.45,
                "Yesterday, 9:20 AM",
                "Contactless",
                "coffee",
            ),
            (
                "tx-104",
                "Spotify Subscription",
                "Entertainment",
                11.99,
                "2 days ago",
                "Auto Pay",
                "music",
            ),
            (
                "tx-105",
                "City Water & Power",
                "Housing & Utilities",
                98.50,
                "3 days ago",
                "Bank Transfer",
                "zap",
            ),
        ]
        cursor.executemany(
            """
            INSERT OR REPLACE INTO transactions (id, title, category, amount, date, payment_method, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            transactions,
        )


def init_db(db_path: Optional[str] = None, seed: bool = True) -> None:
    """Initialize the SQLite database schema and seed initial data."""
    with get_db(db_path) as conn:
        create_tables(conn)
        if seed:
            seed_default_data(conn)


# ==========================================
# Data Access Layer / CRUD Helpers
# ==========================================

def get_metric_summary(
    month: Optional[str] = None,
    year: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve MetricSummary record for a specific month/year or the current system month.
    
    The monthly spending overview displays the current month always based on system date,
    even if the table has historical records or records in the future.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        c_month = month or now.strftime("%m")
        c_year = year or now.strftime("%Y")
        
        # Ensure 2-digit month
        if len(c_month) == 1:
            c_month = f"0{c_month}"

        # 1. Attempt to find exact matching record for the given (c_month, c_year)
        cursor.execute(
            """
            SELECT * FROM metric_summary
            WHERE (strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?)
               OR running_month LIKE ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 1;
            """,
            (c_month, c_year, f"{c_year}-{c_month}%"),
        )
        row = cursor.fetchone()
        
        # 2. If no record for the requested month, fallback to the latest record on or before current date
        # (ignoring future records so current month is never overridden by future budgets)
        if not row:
            cursor.execute(
                """
                SELECT * FROM metric_summary
                WHERE running_month <= date('now')
                ORDER BY running_month DESC, id DESC
                LIMIT 1;
                """
            )
            row = cursor.fetchone()

        # 3. If still no record, fallback to any available summary row
        if not row:
            cursor.execute("SELECT * FROM metric_summary ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()

        # Determine budget and target values
        if row:
            record_dict = dict(row)
            monthly_budget = float(record_dict.get("monthly_budget", 3500.00))
            savings_target = float(record_dict.get("savings_target", 800.00))
            record_id = record_dict.get("id")
            updated_at = record_dict.get("updated_at")
            if record_dict.get("running_month") and (f"{c_year}-{c_month}" in str(record_dict.get("running_month"))):
                running_month_str = str(record_dict.get("running_month"))
            else:
                running_month_str = f"{c_year}-{c_month}-01 00:00:00"
        else:
            monthly_budget = 3500.00
            savings_target = 800.00
            record_id = None
            updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
            running_month_str = f"{c_year}-{c_month}-01 00:00:00"

        # Calculate time metrics based on the target month
        try:
            month_dt = datetime.strptime(f"{c_year}-{c_month}-01", "%Y-%m-%d")
        except Exception:
            month_dt = now

        is_current_month = (month_dt.strftime("%Y-%m") == now.strftime("%Y-%m"))
        active_day = now.day if is_current_month else 1

        next_month = month_dt.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)
        total_days = last_day_of_month.day
        days_left = max(0, total_days - active_day) if is_current_month else total_days
        days_elapsed = max(1, active_day)

        # Calculate total_spent for this month from montly_expenses:
        # Showing only the total of expenses of the current month and <= system date
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]
        has_expense_date = "expense_date" in cols

        today_end = now.strftime("%Y-%m-%d 23:59:59")
        today_date = now.strftime("%Y-%m-%d")

        if has_expense_date:
            cursor.execute(
                f"""
                SELECT COALESCE(SUM(amount), 0.0) FROM {tbl}
                WHERE (
                    (
                        (strftime('%m', expense_date) = ? AND strftime('%Y', expense_date) = ?)
                        OR expense_date LIKE ?
                    )
                    AND (date(expense_date) <= date(?) OR expense_date <= ?)
                )
                OR (
                    expense_date IS NULL
                );
                """,
                (c_month, c_year, f"{c_year}-{c_month}%", today_date, today_end),
            )
        else:
            cursor.execute(f"SELECT COALESCE(SUM(amount), 0.0) FROM {tbl};")

        cat_total = cursor.fetchone()[0] or 0.0

        # Also check transactions for the current month and <= system date
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0.0) FROM transactions
            WHERE (
                (strftime('%m', created_at) = ? AND strftime('%Y', created_at) = ?)
                OR created_at LIKE ?
            )
            AND (date(created_at) <= date(?) OR created_at <= ?);
            """,
            (c_month, c_year, f"{c_year}-{c_month}%", today_date, today_end),
        )
        tx_total = cursor.fetchone()[0] or 0.0

        total_spent = round(max(float(cat_total), float(tx_total)), 2)
        remaining_budget = round(max(0.0, monthly_budget - total_spent), 2)
        savings_current = round(max(0.0, min(savings_target, remaining_budget)), 2)
        savings_rate = (
            round((savings_current / (total_spent + savings_current)) * 100, 1)
            if (total_spent + savings_current) > 0
            else 0.0
        )
        daily_average = round(total_spent / days_elapsed, 2)

        pace_expected = (monthly_budget / total_days) * days_elapsed
        if total_spent <= pace_expected:
            spending_status = "on_track"
        elif total_spent <= pace_expected * 1.15:
            spending_status = "warning"
        else:
            spending_status = "exceeded"

        return {
            "id": record_id,
            "running_month": running_month_str,
            "monthly_budget": monthly_budget,
            "total_spent": total_spent,
            "remaining_budget": remaining_budget,
            "savings_target": savings_target,
            "savings_current": savings_current,
            "savings_rate": savings_rate,
            "daily_average": daily_average,
            "days_left_in_month": days_left,
            "spending_status": spending_status,
            "updated_at": updated_at or now.strftime("%Y-%m-%d %H:%M:%S"),
        }


def update_metric_summary(
    monthly_budget: float,
    savings_target: float,
    running_month: Optional[str] = None,
    total_spent: Optional[float] = None,
    savings_current: Optional[float] = None,
    db_path: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update or insert the MetricSummary row for a specific running_month."""
    now = datetime.now()
    target_month = running_month or now.strftime("%Y-%m-%d 00:00:00")
    
    try:
        month_dt = datetime.strptime(target_month[:10], "%Y-%m-%d")
    except Exception:
        month_dt = now

    c_month = month_dt.strftime("%m")
    c_year = month_dt.strftime("%Y")

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM metric_summary
            WHERE (strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?)
               OR running_month LIKE ?
            ORDER BY id DESC LIMIT 1;
            """,
            (c_month, c_year, f"{c_year}-{c_month}%"),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE metric_summary
                SET monthly_budget = ?,
                    savings_target = ?,
                    updated_at = DATETIME('now')
                WHERE id = ?;
                """,
                (monthly_budget, savings_target, existing["id"]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO metric_summary (
                    monthly_budget, savings_target, updated_at, running_month
                ) VALUES (?, ?, DATETIME('now'), ?);
                """,
                (monthly_budget, savings_target, target_month),
            )

    return get_metric_summary(month=c_month, year=c_year, db_path=db_path) or {}


def get_category_expenses(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all monthly expenses / category items with updated percentages."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]
        
        if "expense_date" in cols:
            cursor.execute(f"SELECT id, name, amount, budget, percentage, color, icon, expense_date FROM {tbl};")
        else:
            cursor.execute(f"SELECT id, name, amount, budget, percentage, color, icon FROM {tbl};")
        
        rows = cursor.fetchall()
        if not rows:
            return []

        categories = [dict(r) for r in rows]
        for c in categories:
            if c.get("amount") is None:
                c["amount"] = 0.0
            if not c.get("color"):
                c["color"] = "#6A8D73"

        total = sum(c["amount"] for c in categories)
        for c in categories:
            c["percentage"] = round((c["amount"] / total) * 100, 1) if total > 0 else 0.0

        return categories



def get_recent_transactions(limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve the most recent Transaction records."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, category, amount, date, payment_method, icon
            FROM transactions
            ORDER BY rowid DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def add_transaction(
    id: str,
    title: str,
    category: str,
    amount: float,
    date: str,
    payment_method: str,
    icon: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new transaction and update category + metric summary records."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (id, title, category, amount, date, payment_method, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (id, title, category, amount, date, payment_method, icon),
        )

        tbl = _get_expenses_table_name(cursor)
        # Update monthly expense amount if matching expense exists by name
        cursor.execute(
            f"""
            UPDATE {tbl}
            SET amount = COALESCE(amount, 0) + ?
            WHERE name = ?;
            """,
            (amount, category),
        )

        # Update metric summary updated_at for the running month if record exists
        c_month = datetime.now().strftime("%m")
        c_year = datetime.now().strftime("%Y")
        cursor.execute(
            """
            UPDATE metric_summary
            SET updated_at = DATETIME('now')
            WHERE (strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?)
               OR running_month LIKE ?;
            """,
            (c_month, c_year, f"{c_year}-{c_month}%"),
        )

    return {
        "id": id,
        "title": title,
        "category": category,
        "amount": amount,
        "date": date,
        "payment_method": payment_method,
        "icon": icon,
    }

