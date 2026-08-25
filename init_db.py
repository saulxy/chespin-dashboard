"""CLI Script to initialize or reset the Chespin SQLite database."""

import argparse
from pathlib import Path
import sys

# Ensure app package is importable
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from app.database import init_db, get_connection, create_tables, seed_default_data
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description="Initialize Chespin SQLite Database")
    parser.add_argument(
        "--db-path",
        type=str,
        default=settings.db_path,
        help="Path to SQLite database file (default: from settings)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-seeding default data even if tables already have records",
    )
    args = parser.parse_args()

    print(f"[*] Initializing SQLite database at: {args.db_path}")
    conn = get_connection(args.db_path)
    try:
        create_tables(conn)
        seed_default_data(conn, force=args.force)
        print("[+] SQLite database successfully initialized and seeded.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
