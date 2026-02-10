#!/usr/bin/env python3
"""Normalize legacy article source values in the SQLite articles table."""

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.sources import LEGACY_SOURCE_MAP


def normalize_sources(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        updated_rows = 0
        for legacy_source, canonical_source in LEGACY_SOURCE_MAP.items():
            cursor.execute(
                "UPDATE articles SET source = ? WHERE source = ?",
                (canonical_source, legacy_source),
            )
            updated_rows += cursor.rowcount
        conn.commit()
        return updated_rows
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="articles.db", help="Path to SQLite database")
    args = parser.parse_args()

    updated_rows = normalize_sources(args.db_path)
    print(f"Normalized {updated_rows} article source value(s) in {args.db_path}.")


if __name__ == "__main__":
    main()
