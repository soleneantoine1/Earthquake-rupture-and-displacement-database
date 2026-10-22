#!/usr/bin/env python3
"""Regenerate docs/SCHEMA.md from scripts/schema.py:  python scripts/make_schema_doc.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402

DESC = {
    "observations": "One published value (or range / category) for one event, metric, study.",
    "arrays": "Header of an along-fault series published as a table/supplement.",
    "array_values": "One measurement of an array (value, optional positive offsets, optional lat/lon).",
    "events": "The earthquake catalogue (one row per physical earthquake).",
    "event_aliases": "Other names/ids that resolve to an event.",
    "metrics": "The metric catalogue (units, allowed statistics, plausible range).",
    "sources": "Atomic publications, databases, agencies, catalogues.",
}
CONVENTIONS = """
## Conventions
- Empty string = missing. Never `0`, `NA`, `-`.
- `unc_minus`/`unc_plus` are **positive offsets** from `value_num` (value - minus, value + plus). The build converts them to absolute bounds (`uncertainty_lower/upper` in `data.js`).
- `value_num` with `qualifier` (`<`,`>`,`~`) is a bound, not a measurement; `value_lo/value_hi` is a published range. Neither is ever plotted as a point.
- `pub_ids` is pipe-separated for joint attribution; `compiled_in` is a single `pub_id`.
- Arrays: `derive_stats=true` -> the build computes min/mean/median/max (never stored).
- OFD and SSD exist only as `off_fault_deformation_fraction` and `ssd_fraction` (unit `%`).
"""


def main():
    out = ["# Schema (generated from `scripts/schema.py` by `scripts/make_schema_doc.py` - that file is authoritative)\n"]
    for n, c in schema.COLUMNS.items():
        out.append(f"## `{n}`  (primary key: {', '.join(schema.PRIMARY_KEYS[n])})\n{DESC[n]}\n\n`" + "`, `".join(c) + "`\n")
    out.append("## Controlled vocabularies\n")
    for v in ("STATISTICS", "UNC_TYPES", "ORIGINS", "RANGE_TYPES", "ALIAS_TYPES", "REVIEW_STATUS", "QUALITY", "QUALIFIERS",
              "FLAGS", "COMPONENTS", "KINDS", "MECHANISMS"):
        out.append(f"- **{v}**: " + ", ".join(f"`{x}`" if x else "`(empty)`" for x in getattr(schema, v)))
    out.append("\n## Keys\n- Duplicate key (same study, same value twice -> error D001): `" + ", ".join(schema.DUPLICATE_KEY) +
               "`\n- Conflict key (one study, two different values -> error D002 unless distinguished): `" + ", ".join(schema.CONFLICT_KEY) + "`")
    out.append(CONVENTIONS)
    (schema.ROOT / "docs" / "SCHEMA.md").write_text("\n".join(out) + "\n", encoding="utf8")
    print("docs/SCHEMA.md written")


if __name__ == "__main__":
    main()
