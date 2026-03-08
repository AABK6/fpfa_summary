#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.article_repository import ArticleRepository, resolve_articles_db_path

DEFAULT_BACKUP = ROOT / '.sync_backups' / 'articles.db.before-cloud-sync-20260306-103711'


def _parse_date_added(raw_value: Any) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value.replace(microsecond=0)
    text_value = str(raw_value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
        try:
            return datetime.strptime(text_value, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(text_value)


def load_backup_rows(backup_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(backup_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT url, date_added
            FROM articles
            WHERE date_added IS NOT NULL AND trim(date_added) <> ''
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            'url': str(row['url']),
            'date_added_text': str(row['date_added']),
            'date_added_dt': _parse_date_added(row['date_added']),
        }
        for row in rows
    ]


def count_matching_urls_sqlite(*, backup_rows: list[dict[str, Any]], target_path: Path) -> int:
    conn = sqlite3.connect(str(target_path))
    try:
        urls = [row['url'] for row in backup_rows]
        chunk_size = 500
        total = 0
        for start in range(0, len(urls), chunk_size):
            batch = urls[start:start + chunk_size]
            placeholders = ','.join('?' for _ in batch)
            total += conn.execute(
                f'SELECT COUNT(*) FROM articles WHERE url IN ({placeholders})',
                batch,
            ).fetchone()[0]
        return total
    finally:
        conn.close()


def restore_sqlite(*, backup_rows: list[dict[str, Any]], target_path: Path) -> tuple[int, int]:
    conn = sqlite3.connect(str(target_path))
    try:
        total_rows = conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
        cur = conn.cursor()
        cur.executemany(
            'UPDATE articles SET date_added = ? WHERE url = ?',
            [(row['date_added_text'], row['url']) for row in backup_rows],
        )
        conn.commit()
        updated = cur.rowcount
        return updated, total_rows
    finally:
        conn.close()


def restore_remote(*, backup_rows: list[dict[str, Any]], target_url: str) -> tuple[int, int]:
    repo = ArticleRepository(database_url=target_url)
    try:
        with repo.engine.connect() as conn:
            total_rows = conn.execute(text('SELECT COUNT(*) FROM articles')).scalar_one()
            matched = 0
            chunk_size = 500
            for start in range(0, len(backup_rows), chunk_size):
                batch = backup_rows[start:start + chunk_size]
                params = {f'url_{idx}': row['url'] for idx, row in enumerate(batch)}
                placeholders = ', '.join(f':url_{idx}' for idx, _ in enumerate(batch))
                matched += conn.execute(
                    text(f'SELECT COUNT(*) FROM articles WHERE url IN ({placeholders})'),
                    params,
                ).scalar_one()
        with repo.engine.begin() as conn:
            conn.execute(
                text('UPDATE articles SET date_added = :date_added WHERE url = :url'),
                [
                    {'url': row['url'], 'date_added': row['date_added_dt']}
                    for row in backup_rows
                ],
            )
        return matched, total_rows
    finally:
        repo.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Restore date_added values from a trusted SQLite backup.')
    parser.add_argument('--backup', default=str(DEFAULT_BACKUP), help='Path to trusted backup SQLite DB.')
    parser.add_argument('--restore-local', action='store_true', help='Restore the local SQLite DB.')
    parser.add_argument('--target-sqlite', default=resolve_articles_db_path(), help='Target local SQLite DB path.')
    parser.add_argument('--backup-local-copy', action='store_true', help='Create a safety copy of the target SQLite DB before restoring.')
    parser.add_argument('--restore-remote', action='store_true', help='Restore the remote DATABASE_URL target.')
    parser.add_argument('--target-url', help='Target remote database URL.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backup_path = Path(args.backup).resolve()
    if not backup_path.exists():
        print(f'Error: backup not found: {backup_path}')
        return 1

    backup_rows = load_backup_rows(backup_path)
    if not backup_rows:
        print('Error: backup did not contain any dated rows.')
        return 1

    print(f'Loaded {len(backup_rows)} backup date mappings from {backup_path}.')

    if args.restore_local:
        target_path = Path(args.target_sqlite).resolve()
        if args.backup_local_copy:
            safety_copy = target_path.with_name(target_path.name + f'.pre-date-restore-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
            shutil.copy2(target_path, safety_copy)
            print(f'Created local safety copy at {safety_copy}.')
        matched = count_matching_urls_sqlite(backup_rows=backup_rows, target_path=target_path)
        updated, total_rows = restore_sqlite(backup_rows=backup_rows, target_path=target_path)
        print(f'Local restore complete. matched_urls={matched} total_rows={total_rows} updated_statements={updated}')

    if args.restore_remote:
        target_url = args.target_url
        if not target_url:
            print('Error: --restore-remote requires --target-url.')
            return 1
        matched, total_rows = restore_remote(backup_rows=backup_rows, target_url=target_url)
        print(f'Remote restore complete. matched_urls={matched} total_rows={total_rows}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
