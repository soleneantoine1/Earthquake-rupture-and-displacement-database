from __future__ import annotations

import argparse
from pathlib import Path

from earthquake_db.database import initialize_database, seeded_metric_ids, table_names


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize a Ridgecrest SQLite database"
    )
    parser.add_argument("database", type=Path, help="path for the SQLite database")
    args = parser.parse_args()

    engine = initialize_database(args.database)
    print(f"Initialized SQLite database: {args.database}")
    print("Tables:")
    for name in table_names(engine):
        print(f"- {name}")
    print("Seeded metric IDs:")
    for metric_id in seeded_metric_ids(engine):
        print(f"- {metric_id}")


if __name__ == "__main__":
    main()
