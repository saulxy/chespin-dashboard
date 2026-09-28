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
    """Return 'montly_expenses' or 'monthly_expenses' if present, otherwise 'category_expenses'."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='montly_expenses';")
    if cursor.fetchone():
        return "montly_expenses"
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_expenses';")
    if cursor.fetchone():
        return "monthly_expenses"
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

def normalize_month_year(val: Optional[str]) -> tuple[str, str]:
    """Extract (YYYY, MM) from strings like '2026-09', '2026-09-01', '09/2026', '2026-9', etc.
    
    Defaults to current system year and month if val is None or empty.
    """
    now = datetime.now()
    if not val:
        return now.strftime("%Y"), now.strftime("%m")
    
    val_str = str(val).strip()
    # Check for YYYY-MM or YYYY-MM-DD
    if len(val_str) >= 7 and val_str[4] == "-":
        parts = val_str.split("-")
        return parts[0], parts[1][:2].zfill(2)
    # Check for MM/YYYY or YYYY/MM
    if "/" in val_str:
        parts = val_str.split("/")
        if len(parts) == 2:
            if len(parts[0]) == 4:
                return parts[0], parts[1][:2].zfill(2)
            else:
                return parts[1][:4], parts[0][:2].zfill(2)
    # If 1-2 digits, assume month of current year
    if len(val_str) <= 2 and val_str.isdigit():
        return now.strftime("%Y"), val_str.zfill(2)
    
    # Try datetime parse as fallback
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m", "%m-%Y", "%Y/%m/%d", "%Y/%m"):
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y"), dt.strftime("%m")
        except ValueError:
            pass

    return now.strftime("%Y"), now.strftime("%m")


def _recalculate_expense_percentages(cursor: sqlite3.Cursor, tbl: str, year: Optional[str] = None, month: Optional[str] = None) -> None:
    """Recalculate percentage of total amount for expenses."""
    cursor.execute(f"PRAGMA table_info({tbl});")
    cols = [r[1] for r in cursor.fetchall()]
    if "expense_date" in cols and year and month:
        cursor.execute(
            f"""
            SELECT id, amount FROM {tbl}
            WHERE (strftime('%Y', expense_date) = ? AND strftime('%m', expense_date) = ?)
               OR expense_date LIKE ?;
            """,
            (year, month, f"{year}-{month}%"),
        )
    else:
        cursor.execute(f"SELECT id, amount FROM {tbl};")
    
    rows = cursor.fetchall()
    if not rows:
        return
    total = sum((r["amount"] or 0.0) for r in rows)
    for r in rows:
        pct = round(((r["amount"] or 0.0) / total) * 100, 1) if total > 0 else 0.0
        cursor.execute(f"UPDATE {tbl} SET percentage = ? WHERE id = ?;", (pct, r["id"]))


def _compute_summary_metrics(
    cursor: sqlite3.Cursor,
    row: Optional[Any],
    c_month: Optional[str] = None,
    c_year: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate all derived metrics for a MetricSummary row or target month."""
    now = datetime.now()
    if row:
        record_dict = dict(row)
        monthly_budget = float(record_dict.get("monthly_budget", 3500.00))
        savings_target = float(record_dict.get("savings_target", 800.00))
        record_id = record_dict.get("id")
        updated_at = record_dict.get("updated_at")
        rm_val = record_dict.get("running_month")
        if not c_month or not c_year:
            c_year, c_month = normalize_month_year(rm_val)
        if rm_val and f"{c_year}-{c_month}" in str(rm_val):
            running_month_str = str(rm_val)
        else:
            running_month_str = f"{c_year}-{c_month}-01 00:00:00"
    else:
        monthly_budget = 3500.00
        savings_target = 800.00
        record_id = None
        updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
        if not c_month:
            c_month = now.strftime("%m")
        if not c_year:
            c_year = now.strftime("%Y")
        running_month_str = f"{c_year}-{c_month}-01 00:00:00"

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

    tbl = _get_expenses_table_name(cursor)
    cursor.execute(f"PRAGMA table_info({tbl});")
    cols = [r[1] for r in cursor.fetchall()]
    has_expense_date = "expense_date" in cols

    today_end = now.strftime("%Y-%m-%d 23:59:59")
    today_date = now.strftime("%Y-%m-%d")

    if has_expense_date:
        if is_current_month:
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
            cursor.execute(
                f"""
                SELECT COALESCE(SUM(amount), 0.0) FROM {tbl}
                WHERE (
                    (strftime('%m', expense_date) = ? AND strftime('%Y', expense_date) = ?)
                    OR expense_date LIKE ?
                );
                """,
                (c_month, c_year, f"{c_year}-{c_month}%"),
            )
    else:
        cursor.execute(f"SELECT COALESCE(SUM(amount), 0.0) FROM {tbl};")

    cat_total = cursor.fetchone()[0] or 0.0

    if is_current_month:
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
    else:
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0.0) FROM transactions
            WHERE (
                (strftime('%m', created_at) = ? AND strftime('%Y', created_at) = ?)
                OR created_at LIKE ?
            );
            """,
            (c_month, c_year, f"{c_year}-{c_month}%"),
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


def preload_monthly_expenses(
    source_month: str,
    target_month: str,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Pre-load (clone) expenses from a source month into a target month.
    
    If source month contains no expenses, raises ValueError asking the user to try again.
    """
    src_year, src_month = normalize_month_year(source_month)
    tgt_year, tgt_month = normalize_month_year(target_month)

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]
        has_expense_date = "expense_date" in cols

        # Query source expenses
        if has_expense_date:
            cursor.execute(
                f"""
                SELECT id, name, amount, budget, percentage, color, icon, expense_date
                FROM {tbl}
                WHERE (strftime('%Y', expense_date) = ? AND strftime('%m', expense_date) = ?)
                   OR expense_date LIKE ?;
                """,
                (src_year, src_month, f"{src_year}-{src_month}%"),
            )
        else:
            cursor.execute(f"SELECT id, name, amount, budget, percentage, color, icon FROM {tbl};")

        source_rows = cursor.fetchall()
        if not source_rows:
            raise ValueError(
                f"No expense data found for month '{src_year}-{src_month}'. "
                "Please try again with a month that contains data."
            )

        # Days in target month
        try:
            tgt_dt = datetime.strptime(f"{tgt_year}-{tgt_month}-01", "%Y-%m-%d")
            next_m = tgt_dt.replace(day=28) + timedelta(days=4)
            last_day = (next_m - timedelta(days=next_m.day)).day
        except Exception:
            last_day = 28

        new_expenses = []
        for r in source_rows:
            row_dict = dict(r)
            src_date = row_dict.get("expense_date")
            day = 1
            if src_date:
                try:
                    day = int(str(src_date)[8:10])
                except Exception:
                    day = 1
            day = min(day, last_day)
            tgt_date_str = f"{tgt_year}-{tgt_month}-{day:02d}"

            if has_expense_date:
                cursor.execute(
                    f"""
                    INSERT INTO {tbl} (name, amount, budget, percentage, color, icon, expense_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        row_dict["name"],
                        row_dict.get("amount", 0.0),
                        row_dict["budget"],
                        row_dict.get("percentage", 0.0),
                        row_dict.get("color") or "#6A8D73",
                        row_dict.get("icon") or "credit-card",
                        tgt_date_str,
                    ),
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {tbl} (name, amount, budget, percentage, color, icon)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        row_dict["name"],
                        row_dict.get("amount", 0.0),
                        row_dict["budget"],
                        row_dict.get("percentage", 0.0),
                        row_dict.get("color") or "#6A8D73",
                        row_dict.get("icon") or "credit-card",
                    ),
                )
            new_id = cursor.lastrowid
            new_expenses.append({
                "id": new_id,
                "name": row_dict["name"],
                "amount": row_dict.get("amount", 0.0),
                "budget": row_dict["budget"],
                "percentage": row_dict.get("percentage", 0.0),
                "color": row_dict.get("color") or "#6A8D73",
                "icon": row_dict.get("icon") or "credit-card",
                "expense_date": tgt_date_str if has_expense_date else None,
            })

        # Recalculate percentages for target month
        _recalculate_expense_percentages(cursor, tbl, tgt_year, tgt_month)

        return new_expenses


def get_metric_summary(
    month: Optional[str] = None,
    year: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve MetricSummary record for a specific month/year or the current system month."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        c_month = month or now.strftime("%m")
        c_year = year or now.strftime("%Y")
        if len(c_month) == 1:
            c_month = f"0{c_month}"

        # 1. Attempt exact match
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
        
        # 2. Fallback to latest record on or before current date
        if not row and not (month or year):
            cursor.execute(
                """
                SELECT * FROM metric_summary
                WHERE running_month <= date('now')
                ORDER BY running_month DESC, id DESC
                LIMIT 1;
                """
            )
            row = cursor.fetchone()

        # 3. Fallback to any summary row
        if not row and not (month or year):
            cursor.execute("SELECT * FROM metric_summary ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()

        if not row and (month or year):
            return None

        return _compute_summary_metrics(cursor, row, c_month=c_month, c_year=c_year)


def get_metric_summary_by_id(summary_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single MetricSummary record by its primary key ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metric_summary WHERE id = ?;", (summary_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _compute_summary_metrics(cursor, row)


def list_metric_summaries(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all MetricSummary records ordered by running_month descending."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metric_summary ORDER BY running_month DESC, id DESC;")
        rows = cursor.fetchall()
        return [_compute_summary_metrics(cursor, row) for row in rows]


def create_metric_summary(
    monthly_budget: float,
    savings_target: float = 0.0,
    running_month: Optional[str] = None,
    preload_from_month: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new MetricSummary record, optionally preloading expenses from a given month."""
    y, m = normalize_month_year(running_month)
    formatted_running_month = f"{y}-{m}-01 00:00:00"

    # If preload requested, clone expenses (raises ValueError if source month has no data)
    if preload_from_month:
        preload_monthly_expenses(
            source_month=preload_from_month,
            target_month=formatted_running_month,
            db_path=db_path,
        )

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO metric_summary (monthly_budget, savings_target, updated_at, running_month)
            VALUES (?, ?, DATETIME('now'), ?);
            """,
            (monthly_budget, savings_target, formatted_running_month),
        )
        new_id = cursor.lastrowid

    return get_metric_summary_by_id(new_id, db_path=db_path) or {}


def update_metric_summary_by_id(
    summary_id: int,
    monthly_budget: Optional[float] = None,
    savings_target: Optional[float] = None,
    running_month: Optional[str] = None,
    preload_from_month: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update an existing MetricSummary record by its ID, optionally preloading expenses."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metric_summary WHERE id = ?;", (summary_id,))
        row = cursor.fetchone()
        if not row:
            return None

        current = dict(row)
        new_budget = monthly_budget if monthly_budget is not None else current["monthly_budget"]
        new_target = savings_target if savings_target is not None else current["savings_target"]
        if running_month:
            y, m = normalize_month_year(running_month)
            new_running_month = f"{y}-{m}-01 00:00:00"
        else:
            new_running_month = current.get("running_month") or datetime.now().strftime("%Y-%m-01 00:00:00")

    if preload_from_month:
        preload_monthly_expenses(
            source_month=preload_from_month,
            target_month=new_running_month,
            db_path=db_path,
        )

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE metric_summary
            SET monthly_budget = ?,
                savings_target = ?,
                running_month = ?,
                updated_at = DATETIME('now')
            WHERE id = ?;
            """,
            (new_budget, new_target, new_running_month, summary_id),
        )

    return get_metric_summary_by_id(summary_id, db_path=db_path)


def delete_metric_summary(summary_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a MetricSummary record by its ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM metric_summary WHERE id = ?;", (summary_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("DELETE FROM metric_summary WHERE id = ?;", (summary_id,))
        return True


def update_metric_summary(
    monthly_budget: float,
    savings_target: float,
    running_month: Optional[str] = None,
    total_spent: Optional[float] = None,
    savings_current: Optional[float] = None,
    preload_from_month: Optional[str] = None,
    db_path: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update or insert the MetricSummary row for a specific running_month."""
    y, m = normalize_month_year(running_month)
    target_month = f"{y}-{m}-01 00:00:00"

    if preload_from_month:
        preload_monthly_expenses(
            source_month=preload_from_month,
            target_month=target_month,
            db_path=db_path,
        )

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM metric_summary
            WHERE (strftime('%m', running_month) = ? AND strftime('%Y', running_month) = ?)
               OR running_month LIKE ?
            ORDER BY id DESC LIMIT 1;
            """,
            (m, y, f"{y}-{m}%"),
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
            ret_id = existing["id"]
        else:
            cursor.execute(
                """
                INSERT INTO metric_summary (
                    monthly_budget, savings_target, updated_at, running_month
                ) VALUES (?, ?, DATETIME('now'), ?);
                """,
                (monthly_budget, savings_target, target_month),
            )
            ret_id = cursor.lastrowid

    return get_metric_summary_by_id(ret_id, db_path=db_path) or {}


# ------------------------------------------
# Monthly Expenses CRUD Helpers
# ------------------------------------------

def create_monthly_expense(
    name: str,
    budget: float,
    amount: float = 0.0,
    color: Optional[str] = "#6A8D73",
    icon: Optional[str] = "credit-card",
    expense_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new MonthlyExpense record in the SQLite database."""
    now = datetime.now()
    exp_date = expense_date or now.strftime("%Y-%m-%d")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]

        if "expense_date" in cols:
            cursor.execute(
                f"""
                INSERT INTO {tbl} (name, amount, budget, percentage, color, icon, expense_date)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (name, amount, budget, 0.0, color or "#6A8D73", icon or "credit-card", exp_date),
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO {tbl} (name, amount, budget, percentage, color, icon)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (name, amount, budget, 0.0, color or "#6A8D73", icon or "credit-card"),
            )
        new_id = cursor.lastrowid

        y, m = normalize_month_year(exp_date)
        _recalculate_expense_percentages(cursor, tbl, y, m)

    return get_monthly_expense_by_id(new_id, db_path=db_path) or {}


def get_monthly_expense_by_id(expense_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single MonthlyExpense record by its ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]

        if "expense_date" in cols:
            cursor.execute(
                f"SELECT id, name, amount, budget, percentage, color, icon, expense_date FROM {tbl} WHERE id = ?;",
                (expense_id,),
            )
        else:
            cursor.execute(
                f"SELECT id, name, amount, budget, percentage, color, icon FROM {tbl} WHERE id = ?;",
                (expense_id,),
            )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("amount") is None:
            res["amount"] = 0.0
        return res


def list_monthly_expenses(
    month: Optional[str] = None,
    year: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all monthly expenses with updated percentages, optionally filtered by month/year."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]
        has_expense_date = "expense_date" in cols

        if month and year and has_expense_date:
            m = month.zfill(2)
            y = str(year)
            cursor.execute(
                f"""
                SELECT id, name, amount, budget, percentage, color, icon, expense_date
                FROM {tbl}
                WHERE (strftime('%m', expense_date) = ? AND strftime('%Y', expense_date) = ?)
                   OR expense_date LIKE ?
                ORDER BY id ASC;
                """,
                (m, y, f"{y}-{m}%"),
            )
        elif has_expense_date:
            cursor.execute(
                f"SELECT id, name, amount, budget, percentage, color, icon, expense_date FROM {tbl} ORDER BY id ASC;"
            )
        else:
            cursor.execute(
                f"SELECT id, name, amount, budget, percentage, color, icon FROM {tbl} ORDER BY id ASC;"
            )

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


def get_category_expenses(
    month: Optional[str] = None,
    year: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve monthly expenses / categories (backward compatible alias for list_monthly_expenses)."""
    return list_monthly_expenses(month=month, year=year, db_path=db_path)


def update_monthly_expense(
    expense_id: int,
    name: Optional[str] = None,
    budget: Optional[float] = None,
    amount: Optional[float] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    expense_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update an existing monthly expense record by ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"SELECT * FROM {tbl} WHERE id = ?;", (expense_id,))
        row = cursor.fetchone()
        if not row:
            return None

        current = dict(row)
        new_name = name if name is not None else current["name"]
        new_budget = budget if budget is not None else current["budget"]
        new_amount = amount if amount is not None else (current.get("amount") or 0.0)
        new_color = color if color is not None else (current.get("color") or "#6A8D73")
        new_icon = icon if icon is not None else (current.get("icon") or "credit-card")

        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]

        if "expense_date" in cols:
            new_date = expense_date if expense_date is not None else current.get("expense_date")
            cursor.execute(
                f"""
                UPDATE {tbl}
                SET name = ?, budget = ?, amount = ?, color = ?, icon = ?, expense_date = ?
                WHERE id = ?;
                """,
                (new_name, new_budget, new_amount, new_color, new_icon, new_date, expense_id),
            )
            y, m = normalize_month_year(new_date)
            _recalculate_expense_percentages(cursor, tbl, y, m)
        else:
            cursor.execute(
                f"""
                UPDATE {tbl}
                SET name = ?, budget = ?, amount = ?, color = ?, icon = ?
                WHERE id = ?;
                """,
                (new_name, new_budget, new_amount, new_color, new_icon, expense_id),
            )
            _recalculate_expense_percentages(cursor, tbl)

    return get_monthly_expense_by_id(expense_id, db_path=db_path)


def delete_monthly_expense(expense_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a monthly expense record by ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        tbl = _get_expenses_table_name(cursor)
        cursor.execute(f"SELECT * FROM {tbl} WHERE id = ?;", (expense_id,))
        row = cursor.fetchone()
        if not row:
            return False

        row_dict = dict(row)
        cursor.execute(f"DELETE FROM {tbl} WHERE id = ?;", (expense_id,))

        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]
        if "expense_date" in cols and row_dict.get("expense_date"):
            y, m = normalize_month_year(row_dict["expense_date"])
            _recalculate_expense_percentages(cursor, tbl, y, m)
        else:
            _recalculate_expense_percentages(cursor, tbl)

        return True




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

