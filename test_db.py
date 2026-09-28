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

        # Test Favicon Endpoints
        r_ico = client.get("/favicon.ico")
        assert r_ico.status_code == 200, f"Root /favicon.ico failed: {r_ico.status_code}"
        assert len(r_ico.content) > 0
        r_static = client.get("/static/favicon.ico")
        assert r_static.status_code == 200, f"/static/favicon.ico failed: {r_static.status_code}"
        print(f"[PASS] Favicon endpoints verified (/favicon.ico, /static/favicon.ico) - {len(r_ico.content)} bytes")

        # ----------------------------------------------------
        # Test Pre-load Expenses Option with No Data (Failure)
        # ----------------------------------------------------
        print("\n=== Testing Pre-load Expenses Error Handling ===")
        # Attempt to create metric_summary pre-loading from a month with no data
        bad_preload_res = client.post(
            "/api/v1/metric-summary",
            json={
                "monthly_budget": 4000.0,
                "savings_target": 500.0,
                "running_month": "2027-01-01",
                "preload_from_month": "1999-12",
            },
        )
        assert bad_preload_res.status_code == 400, f"Expected 400, got: {bad_preload_res.status_code} - {bad_preload_res.text}"
        err_msg = bad_preload_res.json().get("detail", "")
        assert "No expense data found for month" in err_msg and "Please try again" in err_msg, f"Unexpected error msg: {err_msg}"
        print(f"[PASS] Pre-load with empty month correctly rejected with 400: '{err_msg}'")

        # ----------------------------------------------------
        # Test Metric Summary CRUD & Successful Pre-load
        # ----------------------------------------------------
        print("\n=== Testing Metric Summary CRUD ===")
        # 1. Create with successful preload from 2026-09
        create_res = client.post(
            "/api/v1/metric-summary",
            json={
                "monthly_budget": 5200.0,
                "savings_target": 600.0,
                "running_month": "2026-11-01",
                "preload_from_month": "2026-09",
            },
        )
        assert create_res.status_code == 201, f"Create failed: {create_res.text}"
        created_summary = create_res.json()
        summary_id = created_summary["id"]
        assert created_summary["monthly_budget"] == 5200.0
        assert "2026-11" in created_summary["running_month"]
        print(f"[PASS] Created metric summary ID {summary_id} with preloaded expenses.")

        # Check expenses were indeed preloaded into 2026-11
        nov_expenses = client.get("/api/v1/expenses/monthly?month=11&year=2026").json()
        assert len(nov_expenses) > 0, "Preloaded expenses missing for 2026-11"
        print(f"[PASS] Pre-loaded {len(nov_expenses)} expenses into 2026-11 from 2026-09.")

        # 2. Read single summary by ID
        get_res = client.get(f"/api/v1/metric-summary/{summary_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == summary_id
        print(f"[PASS] GET /api/v1/metric-summary/{summary_id} succeeded.")

        # 3. List all summaries
        list_res = client.get("/api/v1/metric-summary")
        assert list_res.status_code == 200
        assert any(item["id"] == summary_id for item in list_res.json())
        print(f"[PASS] GET /api/v1/metric-summary returned {len(list_res.json())} summaries.")

        # 4. Update summary by ID
        update_res = client.put(
            f"/api/v1/metric-summary/{summary_id}",
            json={"monthly_budget": 5500.0, "savings_target": 750.0},
        )
        assert update_res.status_code == 200
        assert update_res.json()["monthly_budget"] == 5500.0
        assert update_res.json()["savings_target"] == 750.0
        print(f"[PASS] PUT /api/v1/metric-summary/{summary_id} updated budget to $5500.0.")

        # 5. Delete summary by ID
        del_res = client.delete(f"/api/v1/metric-summary/{summary_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"
        print(f"[PASS] DELETE /api/v1/metric-summary/{summary_id} succeeded.")

        # ----------------------------------------------------
        # Test Monthly Expenses CRUD
        # ----------------------------------------------------
        print("\n=== Testing Monthly Expenses CRUD ===")
        # 1. Create Monthly Expense with frequency
        new_exp_res = client.post(
            "/api/v1/expenses/monthly",
            json={
                "name": "Gym Membership",
                "budget": 60.0,
                "amount": 45.0,
                "color": "#6A8D73",
                "icon": "dumbbell",
                "expense_date": "2026-09-12",
                "frequency": "weekly",
            },
        )
        assert new_exp_res.status_code == 201, f"Create expense failed: {new_exp_res.text}"
        new_exp = new_exp_res.json()
        exp_id = new_exp["id"]
        assert new_exp["name"] == "Gym Membership"
        assert new_exp["amount"] == 45.0
        assert new_exp.get("frequency") == "weekly", f"Expected frequency 'weekly', got: {new_exp.get('frequency')}"
        print(f"[PASS] Created monthly expense ID {exp_id} ({new_exp['name']}) with frequency='{new_exp['frequency']}'.")

        # 2. Read single expense by ID
        get_exp_res = client.get(f"/api/v1/expenses/monthly/{exp_id}")
        assert get_exp_res.status_code == 200
        assert get_exp_res.json()["name"] == "Gym Membership"
        assert get_exp_res.json().get("frequency") == "weekly"
        print(f"[PASS] GET /api/v1/expenses/monthly/{exp_id} verified with frequency='weekly'.")

        # 3. Update expense by ID (including frequency)
        up_exp_res = client.put(
            f"/api/v1/expenses/monthly/{exp_id}",
            json={"amount": 55.0, "budget": 65.0, "frequency": "biweekly"},
        )
        assert up_exp_res.status_code == 200
        assert up_exp_res.json()["amount"] == 55.0
        assert up_exp_res.json().get("frequency") == "biweekly", f"Expected 'biweekly', got: {up_exp_res.json().get('frequency')}"
        print(f"[PASS] PUT /api/v1/expenses/monthly/{exp_id} updated amount to $55.0 and frequency to 'biweekly'.")

        # 4. Delete expense by ID
        del_exp_res = client.delete(f"/api/v1/expenses/monthly/{exp_id}")
        assert del_exp_res.status_code == 200
        assert del_exp_res.json()["status"] == "deleted"
        print(f"[PASS] DELETE /api/v1/expenses/monthly/{exp_id} succeeded.")

        # Clean up any leftover 2026-11 test expenses
        for exp in nov_expenses:
            client.delete(f"/api/v1/expenses/monthly/{exp['id']}")

        # ----------------------------------------------------
        # Test Preload Expenses Endpoint Only Copies 'monthly'
        # ----------------------------------------------------
        print("\n=== Testing Preload Expenses Endpoint Frequency Filtering ===")
        # Seed test expenses in 2026-05: one monthly, one weekly, one one-time
        e_monthly = client.post("/api/v1/expenses/monthly", json={
            "name": "Monthly Netflix", "budget": 20.0, "amount": 20.0, "expense_date": "2026-05-01", "frequency": "monthly"
        }).json()
        e_weekly = client.post("/api/v1/expenses/monthly", json={
            "name": "Weekly Groceries", "budget": 100.0, "amount": 90.0, "expense_date": "2026-05-07", "frequency": "weekly"
        }).json()
        e_onetime = client.post("/api/v1/expenses/monthly", json={
            "name": "One-time Concert", "budget": 150.0, "amount": 150.0, "expense_date": "2026-05-15", "frequency": "one-time"
        }).json()

        # Call preload endpoint from 2026-05 into 2026-06
        preload_res = client.post("/api/v1/metric-summary/preload-expenses", json={
            "source_month": "2026-05",
            "target_month": "2026-06",
        })
        assert preload_res.status_code == 200, f"Preload failed: {preload_res.text}"
        preloaded_items = preload_res.json()
        assert len(preloaded_items) == 1, f"Expected exactly 1 preloaded expense, got: {len(preloaded_items)}"
        assert preloaded_items[0]["name"] == "Monthly Netflix"
        assert preloaded_items[0]["frequency"] == "monthly"
        print(f"[PASS] Preload expenses endpoint only copied monthly recurring expense: '{preloaded_items[0]['name']}' (ignored weekly & one-time).")

        # Clean up test expenses in 2026-05 and 2026-06
        client.delete(f"/api/v1/expenses/monthly/{e_monthly['id']}")
        client.delete(f"/api/v1/expenses/monthly/{e_weekly['id']}")
        client.delete(f"/api/v1/expenses/monthly/{e_onetime['id']}")
        for exp in preloaded_items:
            client.delete(f"/api/v1/expenses/monthly/{exp['id']}")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
