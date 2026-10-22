#!/usr/bin/env python3
"""Validate the canonical tables.  Run before every build and in CI.

  python scripts/validate.py                 check; fail on NEW errors or dropped counts
  python scripts/validate.py --update-baseline   accept the current known issues (review the git diff!)
  python scripts/validate.py --accept-counts     accept current per event x metric counts

The ratchet works like this: issues that already existed when the baseline was taken
(e.g. v7 problems that need a human) are listed in baselines/known_issues.csv and do not
block the build, but any NEW error does, and counts may never silently go down.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema                                 # noqa: E402
from common import read_table, to_float       # noqa: E402

ERR, WARN = "ERROR", "WARNING"
KNOWN = schema.BASELINES / "known_issues.csv"
COUNTS = schema.BASELINES / "counts.csv"


class Issues:
    def __init__(self):
        self.rows = []

    def add(self, sev, code, key, detail):
        self.rows.append(dict(severity=sev, code=code, key=str(key), detail=detail))

    def df(self):
        return pd.DataFrame(self.rows, columns=["severity", "code", "key", "detail"])


def load():
    tabs = {}
    for name, path in schema.FILES.items():
        if not path.exists():
            raise SystemExit(f"missing {path}")
        tabs[name] = read_table(name)
    return tabs


def check_structure(tabs, iss):
    for name, df in tabs.items():
        cols = schema.COLUMNS[name]
        if list(df.columns) != cols:
            iss.add(ERR, "S001", name, f"columns differ: missing {set(cols)-set(df.columns)}, extra {set(df.columns)-set(cols)}")
        pk = schema.PRIMARY_KEYS[name]
        if (df[pk] == "").any(axis=None):
            iss.add(ERR, "S002", name, "empty primary key")
        for k, g in df[df.duplicated(pk, keep=False)].groupby(pk):
            iss.add(ERR, "S002", f"{name}:{k}", "duplicate primary key")
    def enum(name, col, allowed, allow_empty=False):
        df = tabs[name]
        bad = df[~df[col].isin(list(allowed) + ([""] if allow_empty else []))]
        for _, r in bad.iterrows():
            iss.add(ERR, "S003", f"{name}:{r[schema.PRIMARY_KEYS[name][0]]}:{col}", f"'{r[col]}' not in {sorted(allowed)}")
    enum("observations", "statistic", schema.STATISTICS)
    enum("observations", "unc_type", schema.UNC_TYPES)
    enum("observations", "review_status", schema.REVIEW_STATUS)
    enum("observations", "quality", schema.QUALITY)
    enum("observations", "qualifier", schema.QUALIFIERS, allow_empty=True)
    enum("observations", "component", schema.COMPONENTS, allow_empty=True)
    enum("arrays", "component", schema.COMPONENTS, allow_empty=True)
    enum("arrays", "unc_type", schema.UNC_TYPES)
    enum("arrays", "derive_stats", ["true", "false"])
    enum("observations", "range_type", schema.RANGE_TYPES, allow_empty=True)
    enum("observations", "origin", schema.ORIGINS)
    enum("arrays", "origin", schema.ORIGINS)
    enum("observations", "spatial_representation", schema.SPATIAL_REPRESENTATIONS, allow_empty=True)
    enum("arrays", "spatial_representation", schema.SPATIAL_REPRESENTATIONS, allow_empty=True)
    enum("observations", "coordinate_origin", schema.COORD_ORIGINS, allow_empty=True)
    enum("arrays", "coordinate_origin", schema.COORD_ORIGINS, allow_empty=True)
    enum("arrays", "quality", schema.QUALITY, allow_empty=True)
    enum("event_aliases", "alias_type", schema.ALIAS_TYPES)
    enum("sources", "kind", schema.KINDS)
    enum("sources", "needs_full_reference", ["true", "false"])
    enum("metrics", "value_type", ["numeric", "categorical"])
    for name in ("observations", "arrays"):
        for _, r in tabs[name].iterrows():
            for f in filter(None, r["flags"].split("|")):
                if f not in schema.FLAGS:
                    iss.add(ERR, "S003", f"{name}:{r[schema.PRIMARY_KEYS[name][0]]}:flags", f"unknown flag '{f}'")
    for name in ("observations", "arrays"):
        for _, r in tabs[name].iterrows():
            if not r["submitted_by"]:
                iss.add(ERR, "S005", f"{r[schema.PRIMARY_KEYS[name][0]]}", "submitted_by is empty (every record needs a contributor)")
    for col, pat in (("obs_id", schema.ID_PATTERNS["obs_id"]),):
        for v in tabs["observations"][col]:
            if not re.match(pat, v):
                iss.add(ERR, "S004", v, f"{col} does not match {pat}")
    for v in tabs["sources"]["pub_id"]:
        if not re.match(schema.ID_PATTERNS["pub_id"], v):
            iss.add(ERR, "S004", v, "pub_id pattern")
    for _, r in tabs["sources"].iterrows():
        if r["doi"] and not re.match(r"^10\.\d{4,9}/\S+$", r["doi"]):
            iss.add(ERR, "P002", r["pub_id"], f"malformed DOI '{r['doi']}'")
    d = tabs["sources"][tabs["sources"].doi != ""]
    for doi, g in d.assign(k=d.doi.str.lower()).groupby("k"):
        if len(g) > 1:
            iss.add(ERR, "P003", doi, f"DOI shared by {list(g.pub_id)} - merge these publications")


def check_foreign_keys(tabs, iss):
    ev, mt, so = set(tabs["events"].event_id), set(tabs["metrics"].metric_id), set(tabs["sources"].pub_id)
    for name in ("observations", "arrays"):
        pk = schema.PRIMARY_KEYS[name][0]
        for _, r in tabs[name].iterrows():
            if r["event_id"] not in ev:
                iss.add(ERR, "F001", f"{r[pk]}", f"event_id '{r['event_id']}' not in events")
            if r["metric_id"] not in mt:
                iss.add(ERR, "F002", f"{r[pk]}", f"metric_id '{r['metric_id']}' not in metrics")
            for p in filter(None, r["pub_ids"].split("|")):
                if p not in so:
                    iss.add(ERR, "F003", f"{r[pk]}", f"pub_id '{p}' not in sources")
            if not r["pub_ids"]:
                iss.add(ERR, "F003", f"{r[pk]}", "no pub_ids")
            if r["compiled_in"] and r["compiled_in"] not in so:
                iss.add(ERR, "F004", f"{r[pk]}", f"compiled_in '{r['compiled_in']}' not in sources")
    arr = set(tabs["arrays"].array_id)
    for a in set(tabs["array_values"].array_id) - arr:
        iss.add(ERR, "F006", a, "array_values rows for an unknown array")
    for _, r in tabs["event_aliases"].iterrows():
        if r["event_id"] not in ev:
            iss.add(ERR, "F007", r["alias"], f"alias target {r['event_id']} not in events")
        if r["alias"] in ev:
            iss.add(ERR, "F007", r["alias"], "alias is also a live event id")


def check_values(tabs, iss):
    mt = tabs["metrics"].set_index("metric_id")
    for _, r in tabs["observations"].iterrows():
        oid, m = r["obs_id"], mt.loc[r["metric_id"]] if r["metric_id"] in mt.index else None
        if m is None:
            continue
        num = m["value_type"] == "numeric"
        vn, lo, hi = to_float(r["value_num"]), to_float(r["value_lo"]), to_float(r["value_hi"])
        curated = "needs_curation_unparsed_text" in r["flags"]
        if num:
            if vn is None and (lo is None or hi is None) and not curated:
                iss.add(ERR, "V001", oid, f"numeric metric {r['metric_id']} without a number (value_text='{r['value_text'][:40]}')")
            if r["statistic"] not in schema.NUMERIC_STATS:
                iss.add(ERR, "V002", oid, f"statistic '{r['statistic']}' not allowed for numeric metric")
        else:
            if r["value_text"] == "":
                iss.add(ERR, "V001", oid, "categorical metric without value_text")
            if r["statistic"] != "category":
                iss.add(ERR, "V002", oid, f"categorical metric must use statistic 'category', got '{r['statistic']}'")
        if (lo is not None or hi is not None) and not r["range_type"]:
            iss.add(ERR, "V007", oid, "value_lo/value_hi given without range_type (a published interval is not an uncertainty)")
        if r["range_type"] and lo is None and hi is None:
            iss.add(ERR, "V007", oid, "range_type given without value_lo/value_hi")
        if lo is not None and hi is not None and lo > hi:
            iss.add(ERR, "V005", oid, f"value_lo {lo} > value_hi {hi}")
        if r["qualifier"] and vn is None:
            iss.add(ERR, "V006", oid, "qualifier without value_num")
        cu = m["canonical_unit"]
        if num and cu and r["unit"] and r["unit"] != cu:
            iss.add(ERR, "V003", oid, f"unit '{r['unit']}' != canonical '{cu}' for {r['metric_id']}")
        pmin, pmax = to_float(m["plausible_min"]), to_float(m["plausible_max"])
        for v in (vn, lo, hi):
            if v is not None and ((pmin is not None and v < pmin) or (pmax is not None and v > pmax)):
                iss.add(WARN, "V004", oid, f"{r['metric_id']} value {v} outside plausible range [{pmin}, {pmax}]")
                break
        # digitization: separate from scientific uncertainty
        if r["origin"] == "figure_digitized":
            if not r["digitization_method"] or to_float(r["digitization_unc"]) is None or to_float(r["digitization_unc"]) <= 0:
                iss.add(ERR, "V008", oid, "figure_digitized needs digitization_method and a positive digitization_unc")
        elif r["digitization_method"] or r["digitization_unc"]:
            iss.add(ERR, "V008", oid, "digitization fields set on a value that is not figure_digitized")
        # verified rows must be traceable
        if r["review_status"] == "verified" and (not r["reported_text"] or not r["reviewed_by"]):
            iss.add(ERR, "V009", oid, "verified rows need reported_text (evidence as printed) and reviewed_by")
        # uncertainty
        um, up = to_float(r["unc_minus"]), to_float(r["unc_plus"])
        if r["unc_type"] in ("1sigma", "2sigma", "ci95", "minmax_range", "unspecified"):
            if um is None and up is None and "needs_curation_uncertainty" not in r["flags"]:
                iss.add(ERR, "U001", oid, f"unc_type {r['unc_type']} but no unc_minus/unc_plus")
        if (um is not None and um <= 0) or (up is not None and up <= 0):
            iss.add(ERR, "U001", oid, "unc_minus/unc_plus must be positive offsets, not zero, signed or absolute bounds")
        if r["unc_type"] == "not_reported" and (um is not None or up is not None):
            iss.add(ERR, "U002", oid, "unc_type not_reported but offsets given")
        if r["unc_type"] == "qualitative" and not r["unc_note"]:
            iss.add(ERR, "U003", oid, "qualitative uncertainty needs unc_note")
        if (um is not None or up is not None) and vn is None:
            iss.add(ERR, "U001", oid, "uncertainty offsets need a central value_num")


_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def check_context(tabs, iss):
    """Optional location / method-context fields (V010-V013): empty is fine, but if given they must be coherent."""
    for name, pk in (("observations", "obs_id"), ("arrays", "array_id")):
        for _, r in tabs[name].iterrows():
            rid = r[pk]
            s, e = r["measurement_start"], r["measurement_end"]
            for lab, v in (("measurement_start", s), ("measurement_end", e)):
                if v and not _DATE.match(v):
                    iss.add(ERR, "V010", rid, f"{lab} '{v}' must be YYYY, YYYY-MM or YYYY-MM-DD")
            pad = lambda v: v + "-00-00"[len(v) - 4:]  # noqa: E731  (2019 -> 2019-00-00)
            if s and e and _DATE.match(s) and _DATE.match(e) and pad(s) > pad(e):
                iss.add(ERR, "V010", rid, "measurement_start is after measurement_end")
            if r["sensitivity_threshold"]:
                if to_float(r["sensitivity_threshold"]) is None:
                    iss.add(ERR, "V012", rid, "sensitivity_threshold must be a number")
                elif not r["sensitivity_threshold_unit"]:
                    iss.add(ERR, "V012", rid, "sensitivity_threshold needs sensitivity_threshold_unit")
            elif r["sensitivity_threshold_unit"]:
                iss.add(ERR, "V012", rid, "sensitivity_threshold_unit without sensitivity_threshold")
            cl = to_float(r["confidence_level"])
            if r["confidence_level"] and (cl is None or not 0 < cl <= 100):
                iss.add(ERR, "V012", rid, "confidence_level must be a number in (0, 100]")
            if r["coordinate_origin"] == "converted":
                for f in ("coordinate_conversion_method", "source_spatial_unit", "source_reference_description"):
                    if not r[f]:
                        iss.add(ERR, "V011", rid, f"coordinate_origin=converted needs {f}")
            if name == "observations":
                lon, lat = to_float(r["longitude"]), to_float(r["latitude"])
                if (lon is None) != (lat is None):
                    iss.add(ERR, "V011", rid, "longitude and latitude must be given together")
                elif lon is not None:
                    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                        iss.add(ERR, "V011", rid, f"coordinates out of range ({lon}, {lat})")
                    if not r["coordinate_origin"]:
                        iss.add(ERR, "V011", rid, "coordinates given without coordinate_origin (source | converted)")
                for f in ("depth_m", "horizontal_location_uncertainty_m", "depth_location_uncertainty_m"):
                    if r[f] and to_float(r[f]) is None:
                        iss.add(ERR, "V011", rid, f"{f} must be a number")
                if r["source_spatial_data"] and not r["source_spatial_unit"]:
                    iss.add(ERR, "V011", rid, "source_spatial_data needs source_spatial_unit")
    av = tabs["array_values"]
    for _, r in av.iterrows():
        lon, lat = to_float(r["lon"]), to_float(r["lat"])
        if (lon is None) != (lat is None) or (lon is not None and not (-180 <= lon <= 180 and -90 <= lat <= 90)):
            iss.add(ERR, "V011", r["array_id"], f"array point {r['idx']}: lat/lon must be given together and in range")


def _valkey(df):
    # string concatenation (not row-wise apply) so that empty tables work too
    return df["value_num"] + "~" + df["qualifier"] + "~" + df["value_lo"] + "~" + df["value_hi"] + "~" + df["value_text"]


def check_duplicates(tabs, iss):
    o = tabs["observations"]
    d = o[o.duplicated(schema.DUPLICATE_KEY, keep=False)]
    for key, g in d.groupby(schema.DUPLICATE_KEY):
        iss.add(ERR, "D001", "|".join(map(str, key)), f"same study reports this value twice: {list(g.obs_id)}")
    stat = o[o.statistic != "individual"].copy()
    stat["val"] = _valkey(stat)
    for key, g in stat.groupby(schema.CONFLICT_KEY):
        if g["val"].nunique() > 1:
            iss.add(ERR, "D002", "|".join(map(str, key)),
                    f"one study, several different '{key[3]}' values with nothing to tell them apart "
                    f"(add model_id / segment / component): {dict(zip(g.obs_id, g.value_num))}")
    ind = o[o.statistic == "individual"].copy()
    ind["val"] = _valkey(ind)
    for key, g in ind.groupby(schema.CONFLICT_KEY):
        if g["val"].nunique() > 1:
            iss.add(WARN, "D003", "|".join(map(str, key)), f"one study, several individual values: {dict(zip(g.obs_id, g.value_num))}")
    # duplicate arrays
    av = tabs["array_values"].copy()
    av["value"] = av["value"].astype(float).round(9)
    sig = av.sort_values(["array_id", "idx", ]).groupby("array_id")["value"].apply(lambda s: tuple(s))
    a = tabs["arrays"].set_index("array_id")
    seen = {}
    for aid, vals in sig.items():
        if aid not in a.index:
            continue
        r = a.loc[aid]
        k = (r.event_id, r.metric_id, r.pub_ids, r.component, r.segment, vals)
        if k in seen:
            iss.add(ERR, "D004", aid, f"identical to array {seen[k]}")
        seen[k] = aid


def check_arrays(tabs, iss):
    av = tabs["array_values"]
    n = av.groupby("array_id").size()
    mt = tabs["metrics"].set_index("metric_id")
    for _, r in tabs["arrays"].iterrows():
        aid = r["array_id"]
        if int(r["n_values"]) != int(n.get(aid, 0)):
            iss.add(ERR, "A001", aid, f"n_values {r['n_values']} != {int(n.get(aid, 0))} rows")
        if r["derive_stats"] == "true" and r["metric_id"] in mt.index and mt.loc[r["metric_id"], "value_type"] != "numeric":
            iss.add(ERR, "A002", aid, "derive_stats on a non-numeric metric")
    for aid, g in av.groupby("array_id"):
        idx = sorted(int(i) for i in g.idx)
        if idx != list(range(len(idx))):
            iss.add(ERR, "A001", aid, "idx is not 0..n-1")
    bad = av[av["value"].map(lambda v: to_float(v) is None).astype(bool)]
    for aid in bad.array_id.unique():
        iss.add(ERR, "A001", aid, "non-numeric array value")
    for col in ("unc_minus", "unc_plus"):
        invalid = av[av[col].map(lambda v: (to_float(v) is not None) and to_float(v) <= 0).astype(bool)]
        for aid in invalid.array_id.unique():
            zero = invalid[(invalid.array_id == aid) & (invalid[col] == "0")]
            negative = invalid[(invalid.array_id == aid) & (invalid[col].map(lambda v: to_float(v) is not None and to_float(v) < 0))]
            if len(zero):
                iss.add(WARN, "A004", aid, f"legacy zero {col} offset(s) require source review; new workbook imports reject zero offsets")
            if len(negative):
                iss.add(ERR, "A003", aid, f"{col} must be a positive offset")
    for _, r in tabs["arrays"].iterrows():
        aid = r["array_id"]
        values = av[av.array_id == aid]
        has_offsets = ((values.unc_minus != "") | (values.unc_plus != "")).any()
        if r["unc_type"] == "not_reported" and has_offsets:
            iss.add(ERR, "A003", aid, "unc_type not_reported but array uncertainty offsets are given")
        if r["unc_type"] == "qualitative" and not r["unc_note"]:
            iss.add(ERR, "A003", aid, "qualitative array uncertainty needs unc_note")


def check_events_and_sources(tabs, iss):
    ev, o, ar = tabs["events"], tabs["observations"], tabs["arrays"]
    used = set(o.event_id) | set(ar.event_id)
    for _, r in ev.iterrows():
        if r["event_id"] not in used:
            iss.add(WARN, "E005", r["event_id"], "event has no observations")
        if r["latitude"] == "" or r["longitude"] == "":
            iss.add(WARN, "E001", r["event_id"], "no coordinates: cannot be shown on the map")
        if r["event_date"] == "":
            iss.add(WARN, "E002", r["event_id"], "no date")
    e = ev[ev.event_date != ""].copy()
    e["d"] = pd.to_datetime(e.event_date, errors="coerce")
    e["n"] = e.event_name.str.lower().str.replace(r"[^a-z]", "", regex=True)
    rows = e.sort_values("d").to_dict("records")
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if pd.isna(a["d"]) or pd.isna(b["d"]):
                continue
            if (b["d"] - a["d"]).days > 2:
                break
            if a["n"][:6] == b["n"][:6] and a["sequence_id"] == b["sequence_id"] == "":
                iss.add(WARN, "E004", f"{a['event_id']}|{b['event_id']}", "possible duplicate event (similar name, dates within 2 days)")
    pubs_used = set(p for s in list(o.pub_ids) + list(ar.pub_ids) for p in s.split("|")) | \
        set(x for x in list(o.compiled_in) + list(ar.compiled_in) if x)
    for p in set(tabs["sources"].pub_id) - pubs_used:
        iss.add(WARN, "P004", p, "publication in sources.csv is not used by any record")


def counts(tabs):
    o = tabs["observations"].groupby(["event_id", "metric_id"]).size().rename("n_obs")
    a = tabs["arrays"].groupby(["event_id", "metric_id"]).size().rename("n_arrays")
    c = pd.concat([o, a], axis=1).fillna(0).astype(int).reset_index()
    c["total"] = c.n_obs + c.n_arrays
    return c.sort_values(["event_id", "metric_id"])


def check_counts(tabs, iss, accept):
    cur = counts(tabs)
    if accept or not COUNTS.exists():
        schema.BASELINES.mkdir(exist_ok=True)
        cur.to_csv(COUNTS, index=False, lineterminator="\n")
        if accept:
            print(f"counts baseline written: {len(cur)} event x metric cells")
        return
    base = pd.read_csv(COUNTS)
    # events that were merged into another event legitimately move their counts
    alias = dict(zip(tabs["event_aliases"].alias, tabs["event_aliases"].event_id))
    base["event_id"] = base.event_id.map(lambda e: alias.get(e, e))
    base = base.groupby(["event_id", "metric_id"], as_index=False)[["n_obs", "n_arrays", "total"]].sum()
    m = base.merge(cur, on=["event_id", "metric_id"], how="left", suffixes=("_base", "_now")).fillna(0)
    for _, r in m[m.total_now < m.total_base].iterrows():
        iss.add(ERR, "C001", f"{r.event_id}|{r.metric_id}", f"records dropped from {int(r.total_base)} to {int(r.total_now)} "
                "(if intended: python scripts/validate.py --accept-counts and commit the diff)")


def collect(tabs):
    """Run every row-level / cross-table check (everything except the count ratchet)."""
    iss = Issues()
    check_structure(tabs, iss)
    check_foreign_keys(tabs, iss)
    check_values(tabs, iss)
    check_duplicates(tabs, iss)
    check_arrays(tabs, iss)
    check_context(tabs, iss)
    check_events_and_sources(tabs, iss)
    return iss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--accept-counts", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    tabs = load()
    iss = collect(tabs)
    check_counts(tabs, iss, args.accept_counts)
    df = iss.df()
    df["id"] = df.code + "|" + df.key
    known = set(pd.read_csv(KNOWN, dtype=str).id) if KNOWN.exists() else set()
    if args.update_baseline:
        schema.BASELINES.mkdir(exist_ok=True)
        errs = df[df.severity == ERR]
        errs[["id", "severity", "code", "detail"]].sort_values("id").to_csv(KNOWN, index=False, lineterminator="\n")
        print(f"baseline written: {len(errs)} known errors (warnings are never baselined)")
        known = set(errs.id)
    new = df[~df.id.isin(known)]
    resolved = known - set(df.id)
    schema.REPORTS.mkdir(exist_ok=True)
    df.assign(known=df.id.isin(known)).drop(columns="id").to_csv(schema.REPORTS / "validation_report.csv", index=False, lineterminator="\n")
    summary = df.groupby(["severity", "code"]).size()
    if not args.quiet:
        print("Current issues by type (known = accepted baseline):")
        for (sev, code), n in summary.items():
            if sev != ERR:
                continue
            k = int(df[(df.code == code) & df.id.isin(known)].shape[0])
            print(f"  {sev:7} {code}  total {n:4}  known {k:4}  NEW {n - k:3}")
    new_err = new[new.severity == ERR]
    new_warn = df[df.severity == WARN]
    if len(resolved):
        print(f"{len(resolved)} known issue(s) are now fixed - run --update-baseline to shrink the baseline")
    if len(new_warn) and not args.quiet:
        by = new_warn.groupby("code").size().to_dict()
        print(f"warnings (never block): {by} - details in reports/validation_report.csv")
    if len(new_err):
        print(f"\nFAIL: {len(new_err)} NEW error(s):")
        for _, r in new_err.head(40).iterrows():
            print(f"  ERROR {r.code} {r.key}: {r.detail}")
        sys.exit(1)
    print("OK: no new errors" + (" (baseline updated)" if args.update_baseline else ""))


if __name__ == "__main__":
    main()
