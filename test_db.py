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
    get_spending_trends,
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
    assert "category_expenses" in tables, "category_expenses table missing"
    assert "spending_trends" in tables, "spending_trends table missing"
    assert "transactions" in tables, "transactions table missing"
    assert "system_status" not in tables, "system_status should NOT be a table in SQLite"
    print("[PASS] Table schema verified.")

    print("\n=== Testing Database Helper Queries ===")
    summary = get_metric_summary()
    assert summary is not None
    assert summary["monthly_budget"] == 3500.00
    print(f"[PASS] Metric summary: {summary['spending_status']}, remaining: ${summary['remaining_budget']}")

    categories = get_category_expenses()
    assert len(categories) == 6
    print(f"[PASS] Category expenses: {len(categories)} categories found.")

    trends = get_spending_trends()
    assert len(trends) == 14
    print(f"[PASS] Spending trends: {len(trends)} trend points found.")

    txs = get_recent_transactions()
    assert len(txs) >= 5
    print(f"[PASS] Recent transactions: {len(txs)} transactions found.")

    print("\n=== Testing FastAPI TestClient Endpoints ===")
    with TestClient(app) as client:
        # Test Summary
        r = client.get("/api/v1/summary")
        assert r.status_code == 200, f"Summary failed: {r.text}"
        data = r.json()
        assert data["monthly_budget"] == 3500.00
        print(f"[PASS] GET /api/v1/summary returned 200: {data['spending_status']}")

        # Test Categories
        r = client.get("/api/v1/expenses/categories")
        assert r.status_code == 200, f"Categories failed: {r.text}"
        assert len(r.json()) == 6
        print(f"[PASS] GET /api/v1/expenses/categories returned 200: {len(r.json())} items")

        # Test Trends
        r = client.get("/api/v1/expenses/trends")
        assert r.status_code == 200, f"Trends failed: {r.text}"
        assert len(r.json()) == 14
        print(f"[PASS] GET /api/v1/expenses/trends returned 200: {len(r.json())} points")

        # Test Transactions
        r = client.get("/api/v1/transactions/recent")
        assert r.status_code == 200, f"Transactions failed: {r.text}"
        assert len(r.json()) >= 5
        print(f"[PASS] GET /api/v1/transactions/recent returned 200: {len(r.json())} items")

        # Test Transaction Creation
        r = client.post(
            "/api/v1/transactions",
            json={
                "title": "Bakery Croissants",
                "category": "Dining & Coffee",
                "amount": 12.50,
                "payment_method": "Contactless",
                "icon": "coffee",
            },
        )
        assert r.status_code == 201, f"Create transaction failed: {r.text}"
        new_tx = r.json()
        assert new_tx["title"] == "Bakery Croissants"
        print(f"[PASS] POST /api/v1/transactions returned 201: {new_tx['id']}")

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
