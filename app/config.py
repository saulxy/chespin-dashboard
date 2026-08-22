"""Configuration settings for Chespin Dashboard."""

import os
from pydantic import BaseModel


class DashboardSettings(BaseModel):
    app_name: str = "Chespin Dashboard"
    app_version: str = "0.1.0"
    host: str = os.getenv("CHspin_HOST", "0.0.0.0")
    port: int = int(os.getenv("CHspin_PORT", "8000"))
    debug: bool = os.getenv("CHspin_DEBUG", "false").lower() == "true"
    refresh_interval_seconds: int = int(os.getenv("CHspin_REFRESH_INTERVAL", "30"))
    currency_symbol: str = "$"


settings = DashboardSettings()
