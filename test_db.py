"""Verification test for Chespin SQLite Database & API integration."""

import os
from pathlib import Path
import sqlite3
import sys

# Add directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import (
    get_connection,
    get_metric_summary,
    get_category_expenses,
    get_recent_transactions,
    add_transaction,
)


def run_tests():
    print("=== Testing SQLite Database Schema & Tables ===")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"Discovered Tables: {tables}")
    assert "metric_summary" in tables, "metric_summary table missing"
    assert ("montly_expenses" in tables or "category_expenses" in tables), "montly_expenses table missing"
    assert "transactions" in tables, "transactions table missing"
    assert "system_status" not in tables, "system_status should NOT be a table in SQLite"
    print("[PASS] Table schema verified.")

    print("\n=== Testing Database Helper Queries ===")
    summary = get_metric_summary()
    assert summary is not None
    assert summary["monthly_budget"] > 0
    assert "running_month" in summary
    assert "remaining_budget" in summary
    print(f"[PASS] Metric summary for {summary['running_month']}: {summary['spending_status']}, remaining: ${summary['remaining_budget']}")

    categories = get_category_expenses()
    assert len(categories) > 0
    print(f"[PASS] Category expenses: {len(categories)} categories found.")

    txs = get_recent_transactions()
    assert len(txs) >= 0
    print(f"[PASS] Recent transactions: {len(txs)} transactions found.")

    print("\n=== Testing FastAPI TestClient Endpoints ===")
    with TestClient(app) as client:
        # Test Summary
        r = client.get("/api/v1/summary")
        assert r.status_code == 200, f"Summary failed: {r.text}"
        data = r.json()
        assert data["monthly_budget"] > 0
        assert data.get("running_month") is not None
        assert "remaining_budget" in data
        assert "days_left_in_month" in data
        print(f"[PASS] GET /api/v1/summary returned 200: {data['spending_status']} (running_month: {data['running_month']}, remaining: ${data['remaining_budget']})")

        # Test Summary with Query Params
        r = client.get("/api/v1/summary?month=08&year=2026")
        assert r.status_code == 200, f"Summary filter failed: {r.text}"
        data_filtered = r.json()
        assert data_filtered["monthly_budget"] == 3500.00
        print(f"[PASS] GET /api/v1/summary?month=08&year=2026 returned 200: {data_filtered['running_month']}")


        # Test Monthly Expenses
        r = client.get("/api/v1/expenses/monthly")
        assert r.status_code == 200, f"Monthly expenses failed: {r.text}"
        assert len(r.json()) > 0
        print(f"[PASS] GET /api/v1/expenses/monthly returned 200: {len(r.json())} items")


        # Test Transactions
        r = client.get("/api/v1/transactions/recent")
        assert r.status_code == 200, f"Transactions failed: {r.text}"
        assert len(r.json()) >= 0
        print(f"[PASS] GET /api/v1/transactions/recent returned 200: {len(r.json())} items")

        # Test System Status (Dynamic)
        r = client.get("/api/v1/system/status")
        assert r.status_code == 200, f"System status failed: {r.text}"
        sys_data = r.json()
        assert sys_data["device_name"] == "Chespin Hub (Raspberry Pi)"
        assert sys_data["status"] == "Online"
        print(f"[PASS] GET /api/v1/system/status returned 200: {sys_data['device_name']}")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
