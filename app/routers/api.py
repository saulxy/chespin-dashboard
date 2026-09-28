"""API endpoints providing budget data, metrics, and kiosk status."""

from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app import database

router = APIRouter(prefix="/api/v1", tags=["Dashboard API"])


# ==========================================
# Pydantic Models: Metric Summary
# ==========================================

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


class MetricSummaryCreate(BaseModel):
    monthly_budget: float = Field(..., gt=0, description="Monthly budget limit in dollars")
    savings_target: float = Field(default=0.0, ge=0, description="Savings target for the month")
    running_month: str = Field(..., description="Target running month, e.g. '2026-10-01' or '2026-10'")
    preload_from_month: Optional[str] = Field(
        default=None,
        description="Optional month to pre-load expenses from, e.g. '2026-09'",
    )


class MetricSummaryUpdate(BaseModel):
    monthly_budget: Optional[float] = None
    total_spent: Optional[float] = None
    savings_target: Optional[float] = None
    savings_current: Optional[float] = None
    running_month: Optional[str] = None
    preload_from_month: Optional[str] = None


class PreloadExpensesRequest(BaseModel):
    source_month: str = Field(..., description="Month containing expense template, e.g. '2026-09'")
    target_month: str = Field(..., description="Target month to copy expenses to, e.g. '2026-10'")
    frequency: Optional[str] = Field(default="monthly", description="Frequency filter for preloading (default: 'monthly')")


# ==========================================
# Pydantic Models: Monthly Expenses
# ==========================================

class MonthlyExpense(BaseModel):
    id: Optional[int] = None
    name: str
    amount: Optional[float] = 0.0
    budget: float
    percentage: Optional[float] = 0.0
    color: Optional[str] = "#6A8D73"
    icon: str = "credit-card"
    expense_date: Optional[str] = None
    frequency: Optional[str] = "monthly"


CategoryExpense = MonthlyExpense  # Backward-compatible alias


class MonthlyExpenseCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Expense name/category")
    budget: float = Field(..., ge=0, description="Budget cap for this expense")
    amount: Optional[float] = Field(default=0.0, ge=0, description="Current amount spent")
    color: Optional[str] = Field(default="#6A8D73", description="Color HEX code")
    icon: Optional[str] = Field(default="credit-card", description="Lucide icon name")
    expense_date: Optional[str] = Field(default=None, description="Date of expense (YYYY-MM-DD)")
    frequency: Optional[str] = Field(default="monthly", description="Expense frequency (e.g. monthly, weekly, biweekly, yearly, one-time)")


class MonthlyExpenseUpdate(BaseModel):
    name: Optional[str] = None
    budget: Optional[float] = None
    amount: Optional[float] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    expense_date: Optional[str] = None
    frequency: Optional[str] = None


# ==========================================
# Pydantic Models: Transactions & Status
# ==========================================

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


# ==========================================
# Metric Summary Endpoints
# ==========================================

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
    return MetricSummary(**data)


@router.put("/summary", response_model=MetricSummary)
async def update_summary(summary_update: MetricSummaryUpdate) -> MetricSummary:
    """Update or recalculate budget metric summary for a running month."""
    month_val = summary_update.running_month[5:7] if summary_update.running_month and len(summary_update.running_month) >= 7 else None
    year_val = summary_update.running_month[:4] if summary_update.running_month and len(summary_update.running_month) >= 4 else None

    current = database.get_metric_summary(month=month_val, year=year_val) or {}
    
    monthly_budget = summary_update.monthly_budget if summary_update.monthly_budget is not None else current.get("monthly_budget", 3500.0)
    total_spent = summary_update.total_spent if summary_update.total_spent is not None else current.get("total_spent", 0.0)
    savings_target = summary_update.savings_target if summary_update.savings_target is not None else current.get("savings_target", 800.0)
    savings_current = summary_update.savings_current if summary_update.savings_current is not None else current.get("savings_current", 0.0)

    try:
        updated = database.update_metric_summary(
            monthly_budget=monthly_budget,
            total_spent=total_spent,
            savings_target=savings_target,
            savings_current=savings_current,
            running_month=summary_update.running_month,
            preload_from_month=summary_update.preload_from_month,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return MetricSummary(**updated)


@router.get("/metric-summary", response_model=List[MetricSummary])
async def list_metric_summaries() -> List[MetricSummary]:
    """Retrieve all metric summaries stored in the database."""
    items = database.list_metric_summaries()
    return [MetricSummary(**item) for item in items]


@router.get("/metric-summary/{id}", response_model=MetricSummary)
async def get_metric_summary_by_id(id: int) -> MetricSummary:
    """Retrieve a single metric summary record by ID."""
    item = database.get_metric_summary_by_id(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric summary with ID {id} not found",
        )
    return MetricSummary(**item)


@router.post("/metric-summary", response_model=MetricSummary, status_code=status.HTTP_201_CREATED)
async def create_metric_summary(payload: MetricSummaryCreate) -> MetricSummary:
    """Create a new metric summary, optionally pre-loading expenses from a specified month.
    
    If the specified pre-load month contains no expenses, returns 400 asking to try again.
    """
    try:
        created = database.create_metric_summary(
            monthly_budget=payload.monthly_budget,
            savings_target=payload.savings_target,
            running_month=payload.running_month,
            preload_from_month=payload.preload_from_month,
        )
        return MetricSummary(**created)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/metric-summary/{id}", response_model=MetricSummary)
async def update_metric_summary_by_id(id: int, payload: MetricSummaryUpdate) -> MetricSummary:
    """Update an existing metric summary record by ID, optionally pre-loading expenses."""
    try:
        updated = database.update_metric_summary_by_id(
            summary_id=id,
            monthly_budget=payload.monthly_budget,
            savings_target=payload.savings_target,
            running_month=payload.running_month,
            preload_from_month=payload.preload_from_month,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric summary with ID {id} not found",
            )
        return MetricSummary(**updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/metric-summary/{id}")
async def delete_metric_summary(id: int) -> Dict[str, Any]:
    """Delete a metric summary record by ID."""
    deleted = database.delete_metric_summary(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric summary with ID {id} not found",
        )
    return {"status": "deleted", "id": id}


@router.post("/metric-summary/preload-expenses", response_model=List[MonthlyExpense])
async def preload_expenses_endpoint(payload: PreloadExpensesRequest) -> List[MonthlyExpense]:
    """Copy recurring expenses from a source month into a target month,
    preloading only expenses whose frequency is 'monthly'.
    
    If source month has no matching monthly expenses, returns 400 asking to try again.
    """
    try:
        cloned = database.preload_monthly_expenses(
            source_month=payload.source_month,
            target_month=payload.target_month,
            frequency=payload.frequency or "monthly",
        )
        return [MonthlyExpense(**item) for item in cloned]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# Monthly Expenses Endpoints (CRUD)
# ==========================================

@router.get("/expenses/monthly", response_model=List[MonthlyExpense])
@router.get("/expenses/categories", response_model=List[MonthlyExpense])
async def get_monthly_expenses(
    month: Optional[str] = None,
    year: Optional[str] = None,
) -> List[MonthlyExpense]:
    """Return monthly expense breakdown with budget thresholds from SQLite."""
    items = database.list_monthly_expenses(month=month, year=year)
    return [MonthlyExpense(**item) for item in items]


@router.get("/expenses/monthly/{id}", response_model=MonthlyExpense)
async def get_monthly_expense_by_id(id: int) -> MonthlyExpense:
    """Retrieve a single monthly expense record by ID."""
    item = database.get_monthly_expense_by_id(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monthly expense with ID {id} not found",
        )
    return MonthlyExpense(**item)


@router.post("/expenses/monthly", response_model=MonthlyExpense, status_code=status.HTTP_201_CREATED)
async def create_monthly_expense(payload: MonthlyExpenseCreate) -> MonthlyExpense:
    """Create a new monthly expense record."""
    item = database.create_monthly_expense(
        name=payload.name,
        budget=payload.budget,
        amount=payload.amount or 0.0,
        color=payload.color or "#6A8D73",
        icon=payload.icon or "credit-card",
        expense_date=payload.expense_date,
        frequency=payload.frequency,
    )
    return MonthlyExpense(**item)


@router.put("/expenses/monthly/{id}", response_model=MonthlyExpense)
async def update_monthly_expense(id: int, payload: MonthlyExpenseUpdate) -> MonthlyExpense:
    """Update an existing monthly expense record by ID."""
    updated = database.update_monthly_expense(
        expense_id=id,
        name=payload.name,
        budget=payload.budget,
        amount=payload.amount,
        color=payload.color,
        icon=payload.icon,
        expense_date=payload.expense_date,
        frequency=payload.frequency,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monthly expense with ID {id} not found",
        )
    return MonthlyExpense(**updated)


@router.delete("/expenses/monthly/{id}")
async def delete_monthly_expense(id: int) -> Dict[str, Any]:
    """Delete a monthly expense record by ID."""
    deleted = database.delete_monthly_expense(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monthly expense with ID {id} not found",
        )
    return {"status": "deleted", "id": id}


# ==========================================
# Transactions & System Status Endpoints
# ==========================================

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
