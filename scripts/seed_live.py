#!/usr/bin/env python3
"""Create or normalize the live Ridgecrest-only registry.

This script is intentionally independent of the removed prototype/fixture data.
It keeps the 11 live observations and resets only registries unrelated to them.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402

LIVE = ROOT / "data"

EVENT_COLUMNS = schema.COLUMNS["events"]
ALIAS_COLUMNS = schema.COLUMNS["event_aliases"]
SOURCE_COLUMNS = schema.COLUMNS["sources"]


def main():
    LIVE.mkdir(exist_ok=True)

    events = pd.DataFrame([
        {
            "event_id": "Ridgecrest 1", "event_name": "Ridgecrest 1", "event_date": "2019-07-04",
            "mw": "6.4", "latitude": "35.705", "longitude": "-117.504", "hypocenter_depth_km": "10.5",
            "centroid_depth_km": "5.79", "mechanism": "Strike-slip", "region": "USA",
            "coordinate_source": "SURE 2.0 event table", "sequence_id": "Ridgecrest sequence", "notes": "",
        },
        {
            "event_id": "Ridgecrest 2", "event_name": "Ridgecrest 2", "event_date": "2019-07-06",
            "mw": "7.1", "latitude": "35.77", "longitude": "-117.599", "hypocenter_depth_km": "8",
            "centroid_depth_km": "4.41", "mechanism": "Strike-slip", "region": "USA",
            "coordinate_source": "SURE 2.0 event table", "sequence_id": "Ridgecrest sequence", "notes": "",
        },
    ], columns=EVENT_COLUMNS)
    events.to_csv(LIVE / "events.csv", index=False, lineterminator="\n")

    pd.DataFrame(columns=ALIAS_COLUMNS).to_csv(LIVE / "event_aliases.csv", index=False, lineterminator="\n")

    sources = pd.DataFrame([{
        "pub_id": "antoine_2021",
        "citation_short": "Antoine et al. (2021)",
        "citation_full": "Antoine, S. L., Klinger, Y., Delorme, A., Wang, K., Bürgmann, R., and Gold, R. D. (2021). Diffuse deformation and surface faulting distribution from submetric image correlation along the 2019 Ridgecrest, California, ruptures. Bulletin of the Seismological Society of America. https://doi.org/10.1785/0120210036",
        "doi": "10.1785/0120210036",
        "kind": "publication",
        "needs_full_reference": "false",
        "legacy_source_ids": "",
        "note": "",
    }], columns=SOURCE_COLUMNS)
    sources.to_csv(LIVE / "sources.csv", index=False, lineterminator="\n")

    observations = pd.read_csv(LIVE / "observations.csv", dtype=str, keep_default_na=False)
    observations["event_id"] = observations["event_id"].replace({
        "sure:20190704": "Ridgecrest 1", "sure:20190705": "Ridgecrest 2",
    })
    observations.to_csv(LIVE / "observations.csv", index=False, lineterminator="\n")

    print(f"live registries written: {len(events)} events, "
          f"{len(pd.read_csv(LIVE / 'metrics.csv'))} metrics, {len(sources)} sources")


if __name__ == "__main__":
    main()
