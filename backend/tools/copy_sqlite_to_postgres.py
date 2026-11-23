"""Copy all data from the SQLite database to PostgreSQL (one-time move, e.g. to Neon).

Usage:
    python -m backend.tools.copy_sqlite_to_postgres --source sqlite:///./mustashar.db --target "$DATABASE_URL"

- Creates the tables on the target if needed (and runs the same upgrade steps as the app).
- Copies tables in foreign-key order, then moves each id sequence past the copied ids.
- Refuses to run if the target already has data, so it can't duplicate or overwrite anything.
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import Integer, func, select, text
from sqlmodel import SQLModel

from backend import db


def copy(source_url: str, target_url: str) -> dict[str, int]:
    src = db.make_engine(source_url)
    dst = db.make_engine(target_url)
    if dst.dialect.name != "postgresql":
        raise SystemExit("target must be a PostgreSQL URL")

    db._add_missing_columns(src)  # bring an old SQLite file up to the current columns first
    SQLModel.metadata.create_all(dst)
    tables = SQLModel.metadata.sorted_tables  # parents before children

    with dst.connect() as conn:
        busy = [t.name for t in tables if conn.execute(select(func.count()).select_from(t)).scalar()]
    if busy:
        raise SystemExit(f"target already has data in: {', '.join(busy)}. Use an empty database.")

    counts: dict[str, int] = {}
    with src.connect() as s, dst.begin() as d:
        for table in tables:
            rows = [dict(r._mapping) for r in s.execute(select(table))]
            if rows:
                d.execute(table.insert(), rows)
            counts[table.name] = len(rows)
            pk = list(table.primary_key.columns)
            if len(pk) == 1 and isinstance(pk[0].type, Integer) and rows:
                d.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('\"{table.name}\"', '{pk[0].name}'), "
                    f"(SELECT MAX({pk[0].name}) FROM \"{table.name}\"))"))
    return counts


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--source", default="sqlite:///./mustashar.db")
    p.add_argument("--target", required=True, help="PostgreSQL URL (as given by Neon is fine)")
    args = p.parse_args(argv)
    counts = copy(args.source, args.target)
    for name, n in counts.items():
        print(f"{name:16} {n:6} rows")
    print("done")


if __name__ == "__main__":
    main(sys.argv[1:])
