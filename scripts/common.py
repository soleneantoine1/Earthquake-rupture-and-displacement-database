"""Small shared helpers: CSV reading/writing with deterministic formatting."""
import csv
import hashlib
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402


def fmt_num(x):
    """Deterministic number -> string ('' for missing)."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    try:
        if math.isnan(x):
            return ""
    except TypeError:
        pass
    if float(x) == int(x) and abs(x) < 1e15:
        return str(int(x))
    return f"{float(x):.12g}"


def read_table(name):
    """Read a canonical table as strings (no NaN conversion, '' = missing)."""
    path = schema.FILES[name]
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def write_table(name, df):
    """Write a canonical table: fixed column order, sorted by primary key,
    LF line endings, so that git diffs show only real changes."""
    cols = schema.COLUMNS[name]
    out = df.reindex(columns=cols).fillna("")
    for c in cols:
        out[c] = out[c].map(lambda v: fmt_num(v) if not isinstance(v, str) else v)
    out = out.sort_values(schema.PRIMARY_KEYS[name], kind="stable",
                          key=lambda s: s.map(_sort_key))
    path = schema.FILES[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    return out


def _sort_key(v):
    # numeric-aware sort so that idx 2 comes before idx 10
    try:
        return f"{int(v):012d}"
    except (TypeError, ValueError):
        return str(v)


def to_float(x):
    if x is None or x == "":
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _h(parts):
    return hashlib.sha1("\x1f".join("" if p is None else str(p) for p in parts).encode("utf8")).hexdigest()[:12]


def make_obs_id(row):
    """Deterministic id from the scientific key (same row twice -> same id -> rejected)."""
    return "O" + _h([row.get(k, "") for k in schema.DUPLICATE_KEY])


def make_array_id(row):
    return "A" + _h([row.get(k, "") for k in ("event_id", "metric_id", "pub_ids", "component", "segment", "model_id", "source_location")])
