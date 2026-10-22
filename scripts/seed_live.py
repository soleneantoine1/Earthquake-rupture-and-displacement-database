#!/usr/bin/env python3
"""Create the EMPTY live database (data/) from the migrated v7 fixture.

Kept in the repo as documentation of where the registries came from:
  data/events.csv         <- the 100 events of the v7 catalogue (duplicates merged, see event_aliases.csv)
  data/event_aliases.csv  <- legacy ids / name variants that resolve to those events
  data/metrics.csv        <- the 29-metric catalogue
  data/sources.csv        <- only publications with a DOI and the agencies/catalogues/databases
  data/observations.csv, arrays.csv, array_values.csv  <- EMPTY (headers only)

The unverified v7 observations stay in fixtures/v7_migrated/ (test fixture and demo data).
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402

FIX = ROOT / "fixtures" / "v7_migrated" / "data"
LIVE = ROOT / "data"


def main():
    LIVE.mkdir(exist_ok=True)
    for name in ("events", "event_aliases", "metrics"):
        shutil.copy(FIX / f"{name}.csv", LIVE / f"{name}.csv")
    src = pd.read_csv(FIX / "sources.csv", dtype=str, keep_default_na=False)
    keep = src[(src.doi != "") | (src.kind != "publication")].copy()
    keep["legacy_source_ids"] = ""
    keep.to_csv(LIVE / "sources.csv", index=False, lineterminator="\n")
    for name in ("observations", "arrays", "array_values"):
        pd.DataFrame(columns=schema.COLUMNS[name]).to_csv(LIVE / f"{name}.csv", index=False, lineterminator="\n")
    print(f"live registries written: {len(pd.read_csv(LIVE / 'events.csv'))} events, "
          f"{len(pd.read_csv(LIVE / 'metrics.csv'))} metrics, {len(keep)} sources; observations/arrays empty")


if __name__ == "__main__":
    main()
