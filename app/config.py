"""Configuration settings for Chespin Dashboard."""

import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent


class DashboardSettings(BaseModel):
    app_name: str = "Chespin Dashboard"
    app_version: str = "0.1.0"
    host: str = os.getenv("CHspin_HOST", "0.0.0.0")
    port: int = int(os.getenv("CHspin_PORT", "8000"))
    debug: bool = os.getenv("CHspin_DEBUG", "false").lower() == "true"
    refresh_interval_seconds: int = int(os.getenv("CHspin_REFRESH_INTERVAL", "30"))
    currency_symbol: str = "$"
    db_path: str = os.getenv("CHspin_DB_PATH", str(BASE_DIR / "chespin.db"))


settings = DashboardSettings()

