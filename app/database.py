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


def create_tables(conn: sqlite3.Connection) -> None:
    """Create database tables for API classes if they don't already exist."""
    cursor = conn.cursor()

    # 1. Metric Summary Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metric_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            running_month TEXT NOT NULL DEFAULT (DATE('now')),
            monthly_budget REAL NOT NULL,
            total_spent REAL NOT NULL,
            remaining_budget REAL NOT NULL,
            savings_target REAL NOT NULL,
            savings_current REAL NOT NULL,
            savings_rate REAL NOT NULL,
            daily_average REAL NOT NULL,
            days_left_in_month INTEGER NOT NULL,
            spending_status TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now'))
        );
        """
    )


    # 2. Category Expenses Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS category_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            budget REAL NOT NULL,
            percentage REAL NOT NULL,
            color TEXT NOT NULL,
            icon TEXT NOT NULL
        );
        """
    )

    # 3. Spending Trends Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS spending_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            spent REAL NOT NULL,
            budget_pace REAL NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
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
        next_month = now.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)
        days_left = max(1, (last_day_of_month - now).days)
        days_elapsed = max(1, now.day)

        monthly_budget = 3500.00
        total_spent = 1875.40
        remaining_budget = monthly_budget - total_spent
        savings_target = 800.00
        savings_current = 620.00
        savings_rate = round((savings_current / (total_spent + savings_current)) * 100, 1)
        daily_average = round(total_spent / days_elapsed, 2)

        pace_expected = (monthly_budget / last_day_of_month.day) * days_elapsed
        if total_spent <= pace_expected:
            spending_status = "on_track"
        elif total_spent <= pace_expected * 1.15:
            spending_status = "warning"
        else:
            spending_status = "exceeded"

        if force:
            cursor.execute("DELETE FROM metric_summary;")

        cursor.execute(
            """
            INSERT INTO metric_summary (
                running_month, monthly_budget, total_spent, remaining_budget,
                savings_target, savings_current, savings_rate,
                daily_average, days_left_in_month, spending_status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now'));
            """,
            (
                now.strftime("%Y-%m-%d"),
                monthly_budget,
                total_spent,
                remaining_budget,
                savings_target,
                savings_current,
                savings_rate,
                daily_average,
                days_left,
                spending_status,
            ),
        )

    # Seed Category Expenses
    cursor.execute("SELECT COUNT(*) FROM category_expenses;")
    if cursor.fetchone()[0] == 0 or force:
        if force:
            cursor.execute("DELETE FROM category_expenses;")
        categories = [
            ("Housing & Utilities", 850.00, 900.00, 45.3, "#6A8D73", "home"),
            ("Groceries & Food", 420.50, 550.00, 22.4, "#F0A868", "shopping-cart"),
            ("Dining & Coffee", 195.30, 250.00, 10.4, "#FFE8C2", "coffee"),
            ("Transportation", 165.20, 200.00, 8.8, "#E4FFE1", "car"),
            ("Entertainment", 114.40, 150.00, 6.1, "#F4FDD9", "film"),
            ("Personal & Tech", 130.00, 200.00, 6.9, "#94A89A", "smartphone"),
        ]
        total = sum(c[1] for c in categories)
        cursor.executemany(
            """
            INSERT INTO category_expenses (name, amount, budget, percentage, color, icon)
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

    # Seed Spending Trends (14 days)
    cursor.execute("SELECT COUNT(*) FROM spending_trends;")
    if cursor.fetchone()[0] == 0 or force:
        if force:
            cursor.execute("DELETE FROM spending_trends;")
        now = datetime.now()
        base_spent = 750.0
        daily_pace = 116.6
        trend_rows = []

        for i in range(13, -1, -1):
            day_date = now - timedelta(days=i)
            date_str = day_date.strftime("%b %d")
            day_spend = 60.0 + (i * 7 % 45) + random.uniform(5.0, 25.0)
            base_spent += day_spend
            pace = daily_pace * (14 - i + 5)
            trend_rows.append(
                (date_str, round(base_spent, 2), round(pace, 2), 14 - i)
            )

        cursor.executemany(
            """
            INSERT INTO spending_trends (date, spent, budget_pace, sort_order)
            VALUES (?, ?, ?, ?);
            """,
            trend_rows,
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
    """Retrieve MetricSummary record for a specific month/year or the latest current month."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        c_month = month or datetime.now().strftime("%m")
        c_year = year or datetime.now().strftime("%Y")
        
        # Ensure 2-digit month
        if len(c_month) == 1:
            c_month = f"0{c_month}"

        cursor.execute(
            """
            SELECT * FROM metric_summary
            WHERE strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 1;
            """,
            (c_month, c_year),
        )
        row = cursor.fetchone()
        
        # If no specific record for the given month, fallback to the latest available summary
        if not row:
            cursor.execute("SELECT * FROM metric_summary ORDER BY running_month DESC, id DESC LIMIT 1;")
            row = cursor.fetchone()

        if not row:
            return None
        return dict(row)


def update_metric_summary(
    monthly_budget: float,
    total_spent: float,
    savings_target: float,
    savings_current: float,
    running_month: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Recalculate and update/insert the MetricSummary row for a specific running_month."""
    now = datetime.now()
    target_month = running_month or now.strftime("%Y-%m-%d")
    
    # Try parsing running_month to compute days left & elapsed
    try:
        month_dt = datetime.strptime(target_month[:10], "%Y-%m-%d")
    except Exception:
        month_dt = now

    next_month = month_dt.replace(day=28) + timedelta(days=4)
    last_day_of_month = next_month - timedelta(days=next_month.day)
    days_left = max(1, (last_day_of_month - month_dt).days)
    days_elapsed = max(1, month_dt.day)

    remaining_budget = monthly_budget - total_spent
    savings_rate = (
        round((savings_current / (total_spent + savings_current)) * 100, 1)
        if (total_spent + savings_current) > 0
        else 0.0
    )
    daily_average = round(total_spent / days_elapsed, 2)

    pace_expected = (monthly_budget / last_day_of_month.day) * days_elapsed
    if total_spent <= pace_expected:
        spending_status = "on_track"
    elif total_spent <= pace_expected * 1.15:
        spending_status = "warning"
    else:
        spending_status = "exceeded"

    c_month = month_dt.strftime("%m")
    c_year = month_dt.strftime("%Y")

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        # Check if record for this month exists
        cursor.execute(
            """
            SELECT id FROM metric_summary
            WHERE strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?
            ORDER BY id DESC LIMIT 1;
            """,
            (c_month, c_year),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE metric_summary
                SET monthly_budget = ?,
                    total_spent = ?,
                    remaining_budget = ?,
                    savings_target = ?,
                    savings_current = ?,
                    savings_rate = ?,
                    daily_average = ?,
                    days_left_in_month = ?,
                    spending_status = ?,
                    updated_at = DATETIME('now')
                WHERE id = ?;
                """,
                (
                    monthly_budget,
                    total_spent,
                    remaining_budget,
                    savings_target,
                    savings_current,
                    savings_rate,
                    daily_average,
                    days_left,
                    spending_status,
                    existing["id"],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO metric_summary (
                    running_month, monthly_budget, total_spent, remaining_budget,
                    savings_target, savings_current, savings_rate,
                    daily_average, days_left_in_month, spending_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now'));
                """,
                (
                    target_month,
                    monthly_budget,
                    total_spent,
                    remaining_budget,
                    savings_target,
                    savings_current,
                    savings_rate,
                    daily_average,
                    days_left,
                    spending_status,
                ),
            )
            
    return get_metric_summary(month=c_month, year=c_year, db_path=db_path) or {}


def get_category_expenses(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all CategoryExpense items with updated percentages."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, amount, budget, percentage, color, icon FROM category_expenses;")
        rows = cursor.fetchall()
        
        if not rows:
            return []

        categories = [dict(r) for r in rows]
        total = sum(c["amount"] for c in categories)
        
        # Calculate accurate percentage of total spent
        for c in categories:
            c["percentage"] = round((c["amount"] / total) * 100, 1) if total > 0 else 0.0

        return categories


def get_spending_trends(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all SpendingTrendPoint records ordered chronologically."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date, spent, budget_pace FROM spending_trends ORDER BY sort_order ASC, id ASC;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


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

        # Update category amount if category exists
        cursor.execute(
            """
            UPDATE category_expenses
            SET amount = amount + ?
            WHERE name = ?;
            """,
            (amount, category),
        )

        # Update metric summary total_spent for the running month
        c_month = datetime.now().strftime("%m")
        c_year = datetime.now().strftime("%Y")
        cursor.execute(
            """
            UPDATE metric_summary
            SET total_spent = total_spent + ?,
                remaining_budget = monthly_budget - (total_spent + ?),
                updated_at = DATETIME('now')
            WHERE strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?;
            """,
            (amount, amount, c_month, c_year),
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

