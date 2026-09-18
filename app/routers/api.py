"""API endpoints providing budget data, metrics, and kiosk status."""

from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app import database

router = APIRouter(prefix="/api/v1", tags=["Dashboard API"])


class MetricSummary(BaseModel):
    id: Optional[int] = None
    running_month: Optional[str] = None
    monthly_budget: float
    total_spent: float
    remaining_budget: float
    savings_target: float
    savings_current: float
    savings_rate: float
    daily_average: float
    days_left_in_month: int
    spending_status: str  # "on_track", "warning", "exceeded"
    updated_at: Optional[str] = None


class MetricSummaryUpdate(BaseModel):
    monthly_budget: Optional[float] = None
    total_spent: Optional[float] = None
    savings_target: Optional[float] = None
    savings_current: Optional[float] = None
    running_month: Optional[str] = None



class MonthlyExpense(BaseModel):
    id: Optional[int] = None
    name: str
    amount: Optional[float] = 0.0
    budget: float
    percentage: Optional[float] = 0.0
    color: Optional[str] = "#6A8D73"
    icon: str
    expense_date: Optional[str] = None


CategoryExpense = MonthlyExpense  # Backward-compatible alias




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
async def get_summary(
    month: Optional[str] = None,
    year: Optional[str] = None,
) -> MetricSummary:
    """Return high-level budget overview and KPI statistics from SQLite.
    
    Optionally filters by month (e.g. '08') and year (e.g. '2026').
    Defaults to current month if unspecified.
    """
    data = database.get_metric_summary(month=month, year=year)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric summary not found",
        )
    return MetricSummary(
        id=data.get("id"),
        running_month=data.get("running_month"),
        monthly_budget=data["monthly_budget"],
        total_spent=data["total_spent"],
        remaining_budget=data["remaining_budget"],
        savings_target=data["savings_target"],
        savings_current=data["savings_current"],
        savings_rate=data["savings_rate"],
        daily_average=data["daily_average"],
        days_left_in_month=data["days_left_in_month"],
        spending_status=data["spending_status"],
        updated_at=data.get("updated_at"),
    )


@router.put("/summary", response_model=MetricSummary)
async def update_summary(summary_update: MetricSummaryUpdate) -> MetricSummary:
    """Update or recalculate budget metric summary for a running month."""
    # Determine target month/year
    month_val = summary_update.running_month[5:7] if summary_update.running_month and len(summary_update.running_month) >= 7 else None
    year_val = summary_update.running_month[:4] if summary_update.running_month and len(summary_update.running_month) >= 4 else None

    current = database.get_metric_summary(month=month_val, year=year_val) or {}
    
    monthly_budget = summary_update.monthly_budget if summary_update.monthly_budget is not None else current.get("monthly_budget", 3500.0)
    total_spent = summary_update.total_spent if summary_update.total_spent is not None else current.get("total_spent", 0.0)
    savings_target = summary_update.savings_target if summary_update.savings_target is not None else current.get("savings_target", 800.0)
    savings_current = summary_update.savings_current if summary_update.savings_current is not None else current.get("savings_current", 0.0)

    updated = database.update_metric_summary(
        monthly_budget=monthly_budget,
        total_spent=total_spent,
        savings_target=savings_target,
        savings_current=savings_current,
        running_month=summary_update.running_month,
    )
    return MetricSummary(
        id=updated.get("id"),
        running_month=updated.get("running_month"),
        monthly_budget=updated["monthly_budget"],
        total_spent=updated["total_spent"],
        remaining_budget=updated["remaining_budget"],
        savings_target=updated["savings_target"],
        savings_current=updated["savings_current"],
        savings_rate=updated["savings_rate"],
        daily_average=updated["daily_average"],
        days_left_in_month=updated["days_left_in_month"],
        spending_status=updated["spending_status"],
        updated_at=updated.get("updated_at"),
    )



@router.get("/expenses/monthly", response_model=List[MonthlyExpense])
@router.get("/expenses/categories", response_model=List[MonthlyExpense])
async def get_monthly_expenses() -> List[MonthlyExpense]:
    """Return monthly expense breakdown with budget thresholds from SQLite."""
    items = database.get_category_expenses()
    return [MonthlyExpense(**item) for item in items]





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

