"""SQLite backup and restore-to-new-file operations; never overwrite live data."""

import argparse
import json
import sqlite3
from pathlib import Path


def inspect_database(path: Path) -> dict:
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {"analyses", "scenarios", "drafts", "alembic_version"}
        if not expected <= tables:
            raise ValueError("Database is missing required tables; migrate before backing up")
        return {table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] for table in sorted(expected)}


def copy_database(source: Path, destination: Path) -> dict:
    """SQLite's online backup API produces a consistent snapshot while the app runs."""
    if not source.is_file() or destination.exists() or source.resolve() == destination.resolve():
        raise ValueError("Source must exist and destination must be a new file")
    inspect_database(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids accidental overwrite in a concurrent invocation.
    with destination.open("xb"):
        pass
    with (sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as original,
          sqlite3.connect(destination) as copied):
        original.backup(copied)
    return inspect_database(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["backup", "restore", "inspect"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    if args.operation == "inspect":
        result = inspect_database(args.source)
    else:
        if args.destination is None:
            parser.error("A new destination path is required")
        result = copy_database(args.source, args.destination)
    print(json.dumps({"integrity": "ok", "row_counts": result}))


if __name__ == "__main__":
    main()
