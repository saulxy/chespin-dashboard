#!/usr/bin/env python3
"""Runner script for Chespin Kiosk Dashboard."""

import argparse
import sys
import uvicorn
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description="Run Chespin Kiosk Web Dashboard")
    parser.add_argument(
        "--host",
        type=str,
        default=settings.host,
        help=f"Host address to bind (default: {settings.host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind (default: {settings.port})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.debug,
        help="Enable auto-reloading for development",
    )

    args = parser.parse_args()

    print(f"🌲 Starting Chespin Kiosk Dashboard on http://{args.host}:{args.port}")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
