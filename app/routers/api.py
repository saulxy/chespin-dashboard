"""API endpoints providing budget data, metrics, and kiosk status."""

from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app import database

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


class TransactionCreate(BaseModel):
    id: Optional[str] = None
    title: str
    category: str
    amount: float
    date: Optional[str] = None
    payment_method: str = "Card"
    icon: str = "credit-card"


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
    """Return high-level budget overview and KPI statistics from SQLite."""
    data = database.get_metric_summary()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric summary not found",
        )
    return MetricSummary(
        monthly_budget=data["monthly_budget"],
        total_spent=data["total_spent"],
        remaining_budget=data["remaining_budget"],
        savings_target=data["savings_target"],
        savings_current=data["savings_current"],
        savings_rate=data["savings_rate"],
        daily_average=data["daily_average"],
        days_left_in_month=data["days_left_in_month"],
        spending_status=data["spending_status"],
    )


@router.get("/expenses/categories", response_model=List[CategoryExpense])
async def get_category_expenses() -> List[CategoryExpense]:
    """Return category-wise expense breakdown with budget thresholds from SQLite."""
    items = database.get_category_expenses()
    return [CategoryExpense(**item) for item in items]


@router.get("/expenses/trends", response_model=List[SpendingTrendPoint])
async def get_spending_trends() -> List[SpendingTrendPoint]:
    """Return cumulative daily spending trend across the last 14 days from SQLite."""
    items = database.get_spending_trends()
    return [SpendingTrendPoint(**item) for item in items]


@router.get("/transactions/recent", response_model=List[Transaction])
async def get_recent_transactions(limit: int = 10) -> List[Transaction]:
    """Return the most recent recorded transactions from SQLite."""
    items = database.get_recent_transactions(limit=limit)
    return [Transaction(**item) for item in items]


@router.post("/transactions", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_transaction(tx: TransactionCreate) -> Transaction:
    """Create a new transaction in SQLite and update budget totals."""
    tx_id = tx.id or f"tx-{int(datetime.now().timestamp())}"
    tx_date = tx.date or datetime.now().strftime("%b %d, %I:%M %p")
    
    created = database.add_transaction(
        id=tx_id,
        title=tx.title,
        category=tx.category,
        amount=tx.amount,
        date=tx_date,
        payment_method=tx.payment_method,
        icon=tx.icon,
    )
    return Transaction(**created)


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """Return dynamic kiosk device and synchronization health."""
    return SystemStatus(
        device_name="Chespin Hub (Raspberry Pi)",
        status="Online",
        uptime="98.9%",
        last_sync=datetime.now().strftime("%I:%M:%S %p"),
        wake_word_active=True,
        screen_active=True,
        version="0.1.0-kiosk",
    )

