"""API endpoints providing budget data, metrics, and kiosk status."""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Dashboard API"])


class MetricSummary(BaseModel):
    monthly_budget: float
    total_spent: float
    remaining_budget: float
    savings_target: float
    savings_current: float
    savings_rate: float
    daily_average: float
    days_left_in_month: int
    spending_status: str  # "on_track", "warning", "exceeded"


class CategoryExpense(BaseModel):
    name: str
    amount: float
    budget: float
    percentage: float
    color: str
    icon: str


class SpendingTrendPoint(BaseModel):
    date: str
    spent: float
    budget_pace: float


class Transaction(BaseModel):
    id: str
    title: str
    category: str
    amount: float
    date: str
    payment_method: str
    icon: str


class SystemStatus(BaseModel):
    device_name: str
    status: str
    uptime: str
    last_sync: str
    wake_word_active: bool
    screen_active: bool
    version: str


@router.get("/summary", response_model=MetricSummary)
async def get_summary() -> MetricSummary:
    """Return high-level budget overview and KPI statistics."""
    now = datetime.now()
    # Estimate days left in month
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

    return MetricSummary(
        monthly_budget=monthly_budget,
        total_spent=total_spent,
        remaining_budget=remaining_budget,
        savings_target=savings_target,
        savings_current=savings_current,
        savings_rate=savings_rate,
        daily_average=daily_average,
        days_left_in_month=days_left,
        spending_status=spending_status,
    )


@router.get("/expenses/categories", response_model=List[CategoryExpense])
async def get_category_expenses() -> List[CategoryExpense]:
    """Return category-wise expense breakdown with budget thresholds."""
    categories = [
        {
            "name": "Housing & Utilities",
            "amount": 850.00,
            "budget": 900.00,
            "color": "#6A8D73",  # Sage Green
            "icon": "home",
        },
        {
            "name": "Groceries & Food",
            "amount": 420.50,
            "budget": 550.00,
            "color": "#F0A868",  # Tangerine
            "icon": "shopping-cart",
        },
        {
            "name": "Dining & Coffee",
            "amount": 195.30,
            "budget": 250.00,
            "color": "#FFE8C2",  # Warm Sand
            "icon": "coffee",
        },
        {
            "name": "Transportation",
            "amount": 165.20,
            "budget": 200.00,
            "color": "#E4FFE1",  # Soft Mint
            "icon": "car",
        },
        {
            "name": "Entertainment",
            "amount": 114.40,
            "budget": 150.00,
            "color": "#F4FDD9",  # Pale Cream
            "icon": "film",
        },
        {
            "name": "Personal & Tech",
            "amount": 130.00,
            "budget": 200.00,
            "color": "#94A89A",  # Muted Sage
            "icon": "smartphone",
        },
    ]

    total = sum(c["amount"] for c in categories)
    result = []
    for c in categories:
        result.append(
            CategoryExpense(
                name=c["name"],
                amount=c["amount"],
                budget=c["budget"],
                percentage=round((c["amount"] / total) * 100, 1),
                color=c["color"],
                icon=c["icon"],
            )
        )
    return result


@router.get("/expenses/trends", response_model=List[SpendingTrendPoint])
async def get_spending_trends() -> List[SpendingTrendPoint]:
    """Return cumulative daily spending trend across the last 14 days."""
    points = []
    now = datetime.now()
    base_spent = 750.0
    daily_pace = 116.6  # 3500 / 30

    for i in range(13, -1, -1):
        day_date = now - timedelta(days=i)
        date_str = day_date.strftime("%b %d")
        day_spend = 60.0 + (i * 7 % 45) + random.uniform(5.0, 25.0)
        base_spent += day_spend
        pace = daily_pace * (14 - i + 5)
        points.append(
            SpendingTrendPoint(
                date=date_str,
                spent=round(base_spent, 2),
                budget_pace=round(pace, 2),
            )
        )
    return points


@router.get("/transactions/recent", response_model=List[Transaction])
async def get_recent_transactions() -> List[Transaction]:
    """Return the most recent recorded transactions."""
    return [
        Transaction(
            id="tx-101",
            title="Whole Foods Market",
            category="Groceries & Food",
            amount=64.20,
            date="Today, 3:45 PM",
            payment_method="Apple Pay",
            icon="shopping-cart",
        ),
        Transaction(
            id="tx-102",
            title="Metro Transit Monthly Pass",
            category="Transportation",
            amount=45.00,
            date="Today, 8:15 AM",
            payment_method="Debit Card",
            icon="car",
        ),
        Transaction(
            id="tx-103",
            title="Starbucks Coffee",
            category="Dining & Coffee",
            amount=7.45,
            date="Yesterday, 9:20 AM",
            payment_method="Contactless",
            icon="coffee",
        ),
        Transaction(
            id="tx-104",
            title="Spotify Subscription",
            category="Entertainment",
            amount=11.99,
            date="2 days ago",
            payment_method="Auto Pay",
            icon="music",
        ),
        Transaction(
            id="tx-105",
            title="City Water & Power",
            category="Housing & Utilities",
            amount=98.50,
            date="3 days ago",
            payment_method="Bank Transfer",
            icon="zap",
        ),
    ]


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """Return kiosk device and synchronization health."""
    return SystemStatus(
        device_name="Chespin Hub (Raspberry Pi)",
        status="Online",
        uptime="98.9%",
        last_sync=datetime.now().strftime("%I:%M:%S %p"),
        wake_word_active=True,
        screen_active=True,
        version="0.1.0-kiosk",
    )
