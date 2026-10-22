#!/usr/bin/env python3
"""One-time migration of the ChatGPT/Codex v7 prototype into the canonical tables.

Principles
  * Nothing disappears silently: every one of the 1,942 v7 records gets exactly one
    line in reports/migration_ledger.csv (kept / merged_duplicate / replaced_by_array /
    dropped_placeholder ...).
  * Nothing is invented: values are only parsed, regrouped, de-duplicated or re-labelled.
    Anything ambiguous is flagged and written to reports/curation_queue.csv.
  * Statistics computed from arrays (v7 'database_derived' rows) are NOT stored any more;
    they are verified against the arrays and then re-computed at build time.

Run (fixture only; refuses to touch live data/):
  RUPTURE_DATA_DIR=fixtures/v7_migrated/data RUPTURE_REPORTS_DIR=fixtures/v7_migrated/reports \
  RUPTURE_BASELINES_DIR=fixtures/v7_migrated/baselines python scripts/migrate_v7.py
"""
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema                                   # noqa: E402
from citations import parse_label              # noqa: E402
from common import fmt_num, write_table        # noqa: E402

LEGACY_DB = schema.LEGACY / "v7.sqlite"

# ---------------------------------------------------------------------------
# Decisions taken by hand (each is logged in event_aliases.csv with its reason)
# ---------------------------------------------------------------------------
EVENT_MERGES = {
    "scaling:chichitaiwan:19990921": ("sure:19990920", "Same earthquake (21 Sep is the local date). Literature Mw 7.4-7.6."),
    "scaling:superstitionhillsca:19871123": ("sure:19871124", "Same earthquake listed one day earlier. CONFIRM it is not the Elmore Ranch event (Mw 6.2, 23 Nov local time)."),
    "scaling:pleasantvalleynv:19151002": ("sure:19151003", "Same earthquake (2 Oct is the local date). Literature Mw 6.8-7.3."),
    "scaling:borregomtnca:19680408": ("sure:19680409", "Same earthquake (8 Apr is the local date)."),
    "scaling:luzonphilippines:19900716": ("event:luzon1990", "Same earthquake; literature Mw 7.6-7.7."),
    "scaling:kunlunchina:20011114": ("event:kokoxili", "Same earthquake (Kunlun = Kokoxili 2001)."),
    "scaling:kunlunchinaspot:20011114": ("event:kokoxili", "Same earthquake; SPOT = optical-imagery variant of the same event."),
    "scaling:duzceturkey:19991112": ("event:duzce", "Same earthquake."),
    "event:sakhalin": ("event:neftegorsk1995", "Same earthquake (Sakhalin = Neftegorsk 1995); identical coordinates and Mw."),
    "event:menyuan2022": ("event:menyuan", "Same earthquake (Menyuan 2022 stub)."),
}
EVENT_RENAMES = {"sure:19871124": "Superstition Hills"}   # typo in SURE table
SEQUENCES = {
    "ridgecrest-2019": ["sure:20190704", "sure:20190705"],
    "fairview-dixie-1954": ["sure:19541216", "sure:19541217"],
    "kahramanmaras-2023": ["event:kahramanmarasmw76", "event:kahramanmarasmw78"],
    "kaikoura-2016": ["event:kaikoura2016", "event:kekerengu"],
    "denali-2002": ["sure:20021103", "event:nenanamtn2002"],
}
EVENT_REVIEW_CANDIDATES = [
    ("event:kekerengu", "event:kaikoura2016", "Identical coordinates and Mw. Kekerengu is a fault segment of the 2016 Kaikoura rupture: merge into the event, or keep as a segment-level record?"),
    ("scaling:marryataustralia:19860303", "sure:19860330", "Same name (Marryat); dates differ by 27 days - probably a typo for 1986-03-30."),
]

# The project owner decided (event list notes): OFD and SSD are ingested as fractions (%) only.
EXCLUDED_METRICS = {"off_fault_deformation_absolute", "ssd_absolute"}
ADDED_METRICS = [dict(
    metric_id="surface_afterslip", display_name="Surface afterslip", category="Coseismic surface deformation",
    value_type="numeric", canonical_unit="m", distribution_policy="plot minimum, maximum, mean/average, and median; retain array",
    definition_source="Requested by project owner; definition to be written")]

PLACEHOLDERS = {"", "-", "–", "unknown", "n/a", "na", "nan", "none"}
STAT_MAP = {"individual": "individual", "minimum": "minimum", "mean": "mean",
            "median": "median", "maximum": "maximum", "category": "category"}
NUM = r"-?\d+(?:\.\d+)?"

METRIC_RANGES = {   # plausible_min, plausible_max (canonical units) -- warnings only
    "moment_magnitude": (3, 10), "hypocenter_depth": (0, 100), "centroid_depth": (0, 100),
    "mapped_surface_rupture_length": (0, 1500), "surface_fault_slip": (0, 50),
    "total_surface_displacement": (0, 50), "ssd_fraction": (-300, 100),
    "off_fault_deformation_fraction": (0, 100), "cumulative_fault_displacement": (0, 2000),
    "rupture_velocity": (0, 8), "stress_drop": (0, 100), "fault_slip_rate": (0, 100),
    "surface_rupture_zone_width": (0, 20000),
}


def q(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def nz(x):
    """sqlite NULL / NaN / '' -> None"""
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    if isinstance(x, str) and x.strip() == "":
        return None
    return x


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not (isinstance(x, float) and np.isnan(x))


# ---------------------------------------------------------------------------
def parse_value(raw, value_type):
    """Return dict(value_num, qualifier, value_lo, value_hi, value_text, unc..., reported_text, flags, placeholder)."""
    out = dict(value_num=None, qualifier="", value_lo=None, value_hi=None, value_text="",
               unc_minus=None, unc_plus=None, unc_type=None, unc_note="", reported_text="",
               flags=[], placeholder=False)
    if value_type == "categorical":
        s = str(raw).strip()
        if s.lower() in PLACEHOLDERS:
            out["placeholder"] = True
        out["value_text"] = s
        return out
    if is_num(raw):
        out["value_num"] = float(raw)
        return out
    s = str(raw).strip()
    if s.lower() in PLACEHOLDERS:
        out["placeholder"] = True
        return out
    out["reported_text"] = s
    star = bool(re.search(r"\*", s))
    t = s.replace("*", "").strip()
    if star:
        out["flags"].append("annotation_marker")
    m = re.fullmatch(rf"([<>~≈])?\s*({NUM})", t)
    if m:
        out["qualifier"] = {"≈": "~"}.get(m.group(1) or "", m.group(1) or "")
        out["value_num"] = float(m.group(2))
        return out
    m = re.fullmatch(rf"({NUM})\s*[-–—]\s*({NUM})", t)
    if m:
        out["value_lo"], out["value_hi"] = float(m.group(1)), float(m.group(2))
        out["flags"].append("value_from_range")
        return out
    m = re.fullmatch(rf"({NUM})\s*±\s*({NUM})", t)
    if m:
        out["value_num"] = float(m.group(1))
        out["unc_minus"] = out["unc_plus"] = float(m.group(2))
        out["unc_type"] = "unspecified"
        out["unc_note"] = f'parsed from "{s}"; +/- convention not stated'
        return out
    out["value_text"] = s
    out["flags"].append("needs_curation_unparsed_text")
    return out


def convert_unc(value, lo, hi, utype):
    """v7 stored lower/upper in two incompatible ways (absolute bounds, or symmetric magnitudes).
    Convert to positive offsets; flag what cannot be decided."""
    lo, hi = nz(lo), nz(hi)
    if lo is None and hi is None:
        return "not_reported", None, None, "", None
    if value is None:
        return "unspecified", None, None, f"v7 lower={lo}, upper={hi} without a numeric value", "needs_curation_uncertainty"
    if lo is not None and hi is not None and lo <= value <= hi:
        t = "minmax_range" if utype == "reported_range" else "unspecified"
        note = "published range converted from absolute bounds" if t == "minmax_range" else \
            "v7 stored absolute bounds; converted to offsets; convention (1sigma/CI) not stated"
        return t, value - lo, hi - value, note, None
    if lo is not None and hi is not None and lo == hi and lo >= 0:
        return "unspecified", lo, hi, "v7 stored a symmetric magnitude; convention (1sigma?) not stated", None
    return ("unspecified", None, None,
            f"v7 stored lower={lo}, upper={hi} for value {value}; meaning ambiguous - check the source",
            "needs_curation_uncertainty")


# ---------------------------------------------------------------------------
def main():
    if schema.DATA.resolve() == (schema.ROOT / "data").resolve() and "--force-live" not in sys.argv:
        sys.exit("Refusing to overwrite the LIVE data/ tables (they are meant to stay empty until contributors ingest).\n"
                 "Run against the fixture instead:\n"
                 "  RUPTURE_DATA_DIR=fixtures/v7_migrated/data RUPTURE_REPORTS_DIR=fixtures/v7_migrated/reports \\\n"
                 "  RUPTURE_BASELINES_DIR=fixtures/v7_migrated/baselines python scripts/migrate_v7.py")
    con = sqlite3.connect(f"file:{LEGACY_DB}?mode=ro", uri=True)
    ing = q(con, "select * from ingestion")
    events_v7 = q(con, "select * from event_catalog")
    metrics_v7 = q(con, "select * from metric_definitions")
    sources_v7 = {r["source_id"]: r for r in q(con, "select * from sources")}
    ai = q(con, "select * from array_index")
    av = pd.read_sql("select * from array_values", con)
    for c in ("value", "uncertainty_lower", "uncertainty_upper", "latitude", "longitude"):
        av[c] = pd.to_numeric(av[c], errors="coerce")

    ledger = []     # (legacy_record_id, action, new_id, detail)
    queue = []      # (kind, ref, detail, suggested_action)

    # ---------------- metrics ----------------
    mrows = []
    for m in metrics_v7 + ADDED_METRICS:
        if m["metric_id"] in EXCLUDED_METRICS:
            continue
        numeric = m["value_type"] == "numeric"
        lo, hi = METRIC_RANGES.get(m["metric_id"], (None, None))
        mrows.append(dict(
            metric_id=m["metric_id"], display_name=m["display_name"], category=m["category"],
            value_type=m["value_type"], canonical_unit=nz(m["canonical_unit"]) or "",
            allowed_statistics="|".join(schema.NUMERIC_STATS if numeric else schema.CATEGORICAL_STATS),
            plausible_min=lo, plausible_max=hi,
            distribution_policy=m["distribution_policy"], definition_source=m["definition_source"]))
    metrics = pd.DataFrame(mrows)
    vtype = {m["metric_id"]: m["value_type"] for m in metrics_v7}

    # ---------------- events ----------------
    ev = {e["event_id"]: dict(e) for e in events_v7}
    alias_rows = []
    for alias, (canon, why) in EVENT_MERGES.items():
        a, c = ev[alias], ev[canon]
        for f in ("event_date", "mw", "latitude", "longitude", "hypocenter_depth_km",
                  "centroid_depth_km", "mechanism", "region"):
            if nz(c.get(f)) is None and nz(a.get(f)) is not None:
                c[f] = a[f]
        alias_rows.append(dict(alias=alias, alias_type="legacy_id", event_id=canon, reason=why))
    for eid, name in EVENT_RENAMES.items():
        ev[eid]["event_name"] = name
    seq_of = {e: s for s, es in SEQUENCES.items() for e in es}
    erows = []
    for eid, e in ev.items():
        if eid in EVENT_MERGES:
            continue
        erows.append(dict(
            event_id=eid, event_name=e["event_name"], event_date=nz(e["event_date"]) or "",
            mw=nz(e["mw"]), latitude=nz(e["latitude"]), longitude=nz(e["longitude"]),
            hypocenter_depth_km=nz(e["hypocenter_depth_km"]), centroid_depth_km=nz(e["centroid_depth_km"]),
            mechanism=nz(e["mechanism"]) or "", region=nz(e["region"]) or "",
            coordinate_source=nz(e["coordinate_source"]) or "", sequence_id=seq_of.get(eid, ""), notes=""))
    events = pd.DataFrame(erows)
    for a, b, why in EVENT_REVIEW_CANDIDATES:
        queue.append(("event_merge_candidate", f"{a} | {b}", why, "Decide: merge (add to EVENT_MERGES) or keep separate and set sequence_id/notes"))
    for alias, (canon, why) in EVENT_MERGES.items():
        if "CONFIRM" in why:
            queue.append(("event_merge_confirm", f"{alias} -> {canon}", why, "Confirm the merge or split the records back"))

    def canon_event(eid):
        return EVENT_MERGES.get(eid, (eid, ""))[0]

    # ---------------- sources / publications ----------------
    pubs = {}   # pub_id -> dict
    auth_variants = collections.defaultdict(collections.Counter)
    label_info = {}   # legacy source_id -> (pub_ids list, annotation, label)
    for sid, s in sources_v7.items():
        plist, ann = parse_label(s["citation_label"])
        label_info[sid] = ([p["pub_id"] for p in plist], ann, s["citation_label"])
        for p in plist:
            d = pubs.setdefault(p["pub_id"], dict(pub_id=p["pub_id"], kind=p["kind"], legacy=set(),
                                                    doi="", full="", year=p["year"]))
            d["legacy"].add(sid)
            auth_variants[p["pub_id"]][p["short"]] += 1
        if len(plist) == 1 and nz(s["doi"]):
            pubs[plist[0]["pub_id"]]["doi"] = s["doi"]
    for pid, cnt in auth_variants.items():
        best = sorted(cnt.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[0][0]
        pubs[pid]["short"] = best
    pubs.setdefault("sure2", dict(pub_id="sure2", kind="database", legacy=set(), doi="", full="",
                                  short="SURE 2.0 surface-rupture database", year=""))
    doi_to_pub = {p["doi"].lower(): pid for pid, p in pubs.items() if p["doi"]}

    # full citations: compilation strings (with DOI) and single-study study_reference_full
    def pub_from_compiled(text):
        text = nz(text)
        if text is None:
            return None
        if text.startswith("SURE 2.0"):
            return "sure2"
        m = re.search(r"10\.\d{4,9}/[^\s]+", text)
        if m:
            d = m.group(0).rstrip(".,;)").lower()
            if d in doi_to_pub:
                pubs[doi_to_pub[d]]["full"] = text
                return doi_to_pub[d]
        m = re.match(r"([A-Z][\w\-’']+),.*\((\d{4})\)", text)
        if m:
            from citations import _slug
            pid = f"{_slug(m.group(1))}_{m.group(2)}"
            if pid in pubs:
                pubs[pid]["full"] = pubs[pid]["full"] or text
                return pid
        return None

    full_votes = collections.defaultdict(collections.Counter)
    for r in ing:
        pids, _, label = label_info[r["source_id"]]
        srf = nz(r["study_reference_full"])
        if len(pids) == 1 and srf and srf != label and len(srf) >= 60 and not srf.startswith("Underlying"):
            full_votes[pids[0]][srf] += 1
    for pid, cnt in full_votes.items():
        if not pubs[pid]["full"]:
            pubs[pid]["full"] = cnt.most_common(1)[0][0]

    # ---------------- observations ----------------
    obs, derived_rows = [], []
    for r in ing:
        rid = r["record_id"]
        if r["value_origin"] == "database_derived":
            derived_rows.append(r)
            continue
        mid = r["metric_id"]
        if mid in EXCLUDED_METRICS:
            ledger.append((rid, "dropped_metric_out_of_scope", "", f"{mid}: OFD/SSD are ingested as % fractions only"))
            continue
        pv = parse_value(r["value"], vtype[mid])
        if pv["placeholder"]:
            ledger.append((rid, "dropped_placeholder", "", f'v7 value "{r["value"]}" is an empty placeholder (no data)'))
            continue
        pids, ann, label = label_info[r["source_id"]]
        compiled = pub_from_compiled(r["compiled_in_reference"])
        flags = list(pv["flags"])
        if compiled and compiled in pids and len(pids) == 1:
            if str(nz(r["original_measurement_reference"]) or "").startswith("Underlying"):
                flags.append("original_pub_unresolved")
            compiled = ""
        if ann:
            flags.append("annotation_in_label")
        comp, seg = nz(r["component"]) or "", ""
        if comp and comp not in schema.COMPONENTS:
            seg, comp = comp, ""
            flags.append("segment_moved_from_component")
        # uncertainty
        if pv["unc_type"]:
            utype, um, up, unote, uflag = pv["unc_type"], pv["unc_minus"], pv["unc_plus"], pv["unc_note"], None
        else:
            val = pv["value_num"]
            utype, um, up, unote, uflag = convert_unc(val, r["uncertainty_lower"], r["uncertainty_upper"],
                                                      r["uncertainty_type"])
        if uflag:
            flags.append(uflag)
        unit = nz(r["unit"]) or ""
        if unit == "source text":
            unit = ""
        obs.append(dict(
            obs_id=rid, event_id=canon_event(r["target_id"]), metric_id=mid,
            pub_ids="|".join(sorted(set(pids))), compiled_in=compiled or "",
            statistic=STAT_MAP[r["statistic_type"]],
            value_num=pv["value_num"], qualifier=pv["qualifier"], value_lo=pv["value_lo"],
            value_hi=pv["value_hi"], range_type="published_range" if pv["value_lo"] is not None else "",
            value_text=pv["value_text"], unit=unit,
            component=comp, segment=seg, model_id="", n=nz(r["sample_count"]),
            unc_type=utype, unc_minus=um, unc_plus=up, unc_note=unote, reported_text=pv["reported_text"],
            source_location=nz(r["source_location"]) or "", method=nz(r["method"]) or "",
            method_details=nz(r["method_details"]) or "", origin="reported", digitization_method="",
            digitization_unc=None, review_status=r["review_status"],
            quality=r["quality_flag"], flags="|".join(dict.fromkeys(flags)),
            comment=nz(r["comments"]) or "", legacy_label=label,
            submitted_by="v7 prototype (Codex/ChatGPT)", submitted_on="", reviewed_by="", reviewed_on=""))
    obs = pd.DataFrame(obs)

    # ---------------- arrays ----------------
    av_by = {k: g.sort_values("value_index") for k, g in av.groupby("array_id")}
    group_to_array = {a["observation_group_id"]: a["array_id"] for a in ai}
    derived_by_array = collections.defaultdict(list)
    for r in derived_rows:
        derived_by_array[group_to_array[r["observation_group_id"]]].append(r)

    arr_rows, val_rows, arr_key_seen, dup_array_of = [], [], {}, {}
    for a in ai:
        lid = a["array_id"]
        g = av_by[lid]
        pids, ann, label = label_info[a["source_id"]]
        compiled = "sure2" if str(a["method"]).startswith("SURE 2.0") else ""
        comp, seg = nz(a["component"]) or "", ""
        flags = []
        if comp and comp not in schema.COMPONENTS:
            seg, comp = comp, ""
            flags.append("segment_moved_from_component")
        if ann:
            flags.append("annotation_in_label")
        eid = canon_event(a["event_id"])
        key = (eid, a["metric_id"], tuple(sorted(set(pids))), comp, seg,
               tuple(np.round(g["value"].to_numpy(float), 9)))
        if key in arr_key_seen:
            dup_array_of[lid] = arr_key_seen[key]
            continue
        arr_key_seen[key] = lid
        # uncertainty: either 1-sigma metadata (Milliner) or v7 lower/upper columns (SURE)
        meta = [json.loads(m) if m else {} for m in g["metadata_json"]]
        sig = [m.get("uncertainty_1sigma_m", "x") for m in meta]
        has_sigma_key = any(s != "x" for s in sig)
        lo, hi = g["uncertainty_lower"].to_numpy(float), g["uncertainty_upper"].to_numpy(float)
        has_cols = (~np.isnan(lo) | ~np.isnan(hi)).any()
        if has_sigma_key:
            um = up = np.array([np.nan if s in ("x", None) else float(s) for s in sig])
            utype, unote = "1sigma", "published 1-sigma uncertainty (v7 metadata uncertainty_1sigma_m)"
        elif has_cols:
            um, up = np.abs(lo), np.abs(hi)
            utype = "unspecified"
            unote = "SURE uncertainty columns; v7 mixed signed and unsigned offsets - normalised to positive offsets; convention not stated"
            if ((lo < 0) | (hi < 0)).any():
                unote += " (some rows were negative in v7)"
        else:
            um = up = np.full(len(g), np.nan)
            utype, unote = "not_reported", ""
        arr_rows.append(dict(
            array_id=f"A{int(lid):04d}", event_id=eid, metric_id=a["metric_id"],
            pub_ids="|".join(sorted(set(pids))), compiled_in=compiled, component=comp, segment=seg,
            model_id="", unit=nz(a["unit"]) or "", source_location=nz(a["source_location"]) or "",
            method=nz(a["method"]) or "", method_details="",
            derive_stats="true" if derived_by_array.get(lid) else "false",
            unc_type=utype, unc_note=unote, n_values=len(g), review_status="draft",
            origin="reported", digitization_method="", digitization_unc=None,
            flags="|".join(flags), legacy_array_id=lid,
            submitted_by="v7 prototype (Codex/ChatGPT)", submitted_on="", reviewed_by="", reviewed_on=""))
        for i, (idx, row) in enumerate(g.reset_index(drop=True).iterrows()):
            val_rows.append(dict(array_id=f"A{int(lid):04d}", idx=int(i), value=row["value"],
                                 unc_minus=None if np.isnan(um[i]) else um[i],
                                 unc_plus=None if np.isnan(up[i]) else up[i],
                                 lat=None if np.isnan(row["latitude"]) else row["latitude"],
                                 lon=None if np.isnan(row["longitude"]) else row["longitude"]))
    arrays = pd.DataFrame(arr_rows)
    array_values = pd.DataFrame(val_rows)
    kept_ids = {int(x["legacy_array_id"]) for x in arr_rows}
    # derive_stats must survive when a duplicate array was the one carrying the derived rows
    for dup, keep in dup_array_of.items():
        if derived_by_array.get(dup):
            arrays.loc[arrays.legacy_array_id == keep, "derive_stats"] = "true"

    # ---------------- derived rows: verify against arrays, then retire ----------------
    mismatches = 0
    for r in derived_rows:
        lid = group_to_array[r["observation_group_id"]]
        vals = av_by[lid]["value"].to_numpy(float)
        fn = {"minimum": np.min, "maximum": np.max, "mean": np.mean, "median": np.median}[r["statistic_type"]]
        recomputed = float(fn(vals))
        ok = abs(recomputed - float(r["value"])) <= 1e-9 * max(1.0, abs(recomputed)) and int(r["sample_count"]) == len(vals)
        target = dup_array_of.get(lid, lid)
        if ok:
            act = "replaced_by_array_view" if lid in kept_ids else "replaced_by_array_view_duplicate_array"
            ledger.append((r["record_id"], act, f"A{int(target):04d}",
                           f'{r["statistic_type"]} {r["value"]} recomputed from array = {recomputed:.9g}'))
        else:
            mismatches += 1
            ledger.append((r["record_id"], "KEPT_unverified_derived", "", f"stored {r['value']} != recomputed {recomputed}"))
    assert mismatches == 0, f"{mismatches} derived records do not match their arrays"

    # ---------------- de-duplicate observations ----------------
    def completeness(row):
        return sum(1 for v in row.values if isinstance(v, str) and v != "") + \
               sum(1 for v in row.values if v is not None and not isinstance(v, str) and not pd.isna(v))
    for _c in ("longitude", "latitude"):
        if _c not in obs.columns:
            obs[_c] = ""
    obs["_key"] = obs.apply(lambda r: tuple("" if pd.isna(r[k]) else r[k] for k in schema.DUPLICATE_KEY), axis=1)
    obs["_score"] = obs.apply(lambda r: (0 if r["compiled_in"] == "" else 1, -completeness(r), r["obs_id"]), axis=1)
    keep_idx = []
    for key, g in obs.groupby("_key", sort=False):
        g = g.sort_values("_score")
        keep = g.iloc[0]
        keep_idx.append(g.index[0])
        for _, d in g.iloc[1:].iterrows():
            ledger.append((d["obs_id"], "merged_duplicate", keep["obs_id"],
                           f'same study/event/metric/statistic/value as {keep["obs_id"]} '
                           f'(dropped copy compiled_in="{d["compiled_in"]}", source label "{d["legacy_label"]}")'))
    dropped = set(obs.index) - set(keep_idx)
    obs_final = obs.loc[sorted(keep_idx)].drop(columns=["_key", "_score"])
    for oid in obs_final["obs_id"]:
        ledger.append((oid, "kept", oid, ""))

    # ---------------- sources table ----------------
    srows = []
    used = set()
    for df_ in (obs_final, arrays):
        for s in df_["pub_ids"]:
            used.update(s.split("|"))
        used.update(x for x in df_["compiled_in"] if x)
    for pid, p in sorted(pubs.items()):
        srows.append(dict(
            pub_id=pid, citation_short=p["short"], citation_full=p["full"], doi=p["doi"], kind=p["kind"],
            needs_full_reference="true" if (p["kind"] == "publication" and not p["full"]) else "false",
            legacy_source_ids="|".join(sorted(p["legacy"])), note=""))
    sources = pd.DataFrame(srows)

    # ---------------- curation queue extras ----------------
    for lab, (pids, ann, label) in label_info.items():
        if len(pids) > 1:
            queue.append(("compound_attribution", label,
                          f"{len(pids)} studies share one measurement row: {', '.join(pids)}",
                          "If the values differ by study, split into one row per study"))
    seen_ann = set()
    for lab, (pids, ann, label) in label_info.items():
        if ann and label not in seen_ann:
            seen_ann.add(label)
            queue.append(("annotation_in_label", label, f'footnote text "{ann}" kept in legacy_label',
                          "Move the footnote into comment/method_details of the relevant rows"))
    by_slug = collections.defaultdict(list)
    for pid in pubs:
        m = re.match(r"(.+)_(\d{4})", pid)
        if m:
            by_slug[m.group(1)].append((int(m.group(2)), pid))
    for slug, lst in by_slug.items():
        lst.sort()
        for (y1, p1), (y2, p2) in zip(lst, lst[1:]):
            if 0 < y2 - y1 <= 1:
                queue.append(("near_duplicate_publication", f"{p1} | {p2}",
                              "same first author, years differ by one (possible 1-year citation error)",
                              "Check whether this is one paper; if so merge in sources.csv"))
    for _, r in obs_final.iterrows():
        if "needs_curation_unparsed_text" in r["flags"]:
            queue.append(("unparsed_text_value", r["obs_id"], f'{r["event_id"]} / {r["metric_id"]}: "{r["value_text"][:100]}"',
                          "Enter numeric value(s), unit and the study that each number belongs to"))
        if "needs_curation_uncertainty" in r["flags"]:
            queue.append(("ambiguous_uncertainty", r["obs_id"], r["unc_note"], "Open the paper and set unc_type/unc_minus/unc_plus"))

    # ---------------- write ----------------
    write_table("metrics", metrics)
    write_table("events", events)
    write_table("event_aliases", pd.DataFrame(alias_rows))
    write_table("sources", sources)
    write_table("observations", obs_final)
    write_table("arrays", arrays)
    write_table("array_values", array_values)
    schema.REPORTS.mkdir(exist_ok=True)
    led = pd.DataFrame(ledger, columns=["legacy_record_id", "action", "new_id", "detail"])
    # conservation: every v7 record has exactly one fate
    all_ids = {r["record_id"] for r in ing}
    assert set(led.legacy_record_id) == all_ids and not led.legacy_record_id.duplicated().any(), \
        "ledger does not account for every v7 record exactly once"
    led.sort_values(["legacy_record_id", "action"]).to_csv(schema.REPORTS / "migration_ledger.csv", index=False, lineterminator="\n")
    pd.DataFrame(queue, columns=["kind", "ref", "detail", "suggested_action"]).to_csv(
        schema.REPORTS / "curation_queue.csv", index=False, lineterminator="\n")
    summary = dict(
        legacy_records=len(ing), legacy_reported=len(ing) - len(derived_rows), legacy_derived=len(derived_rows),
        observations_written=len(obs_final), duplicates_merged=len(dropped),
        placeholders_dropped=int((led.action == "dropped_placeholder").sum()),
        derived_replaced_by_array_view=int(led.action.str.startswith("replaced_by_array_view").sum()),
        arrays_v7=len(ai), arrays_written=len(arrays), arrays_duplicate_dropped=len(dup_array_of),
        array_values_written=len(array_values),
        events_v7=len(events_v7), events_written=len(events), events_merged=len(EVENT_MERGES),
        sources_v7=len(sources_v7), publications_written=len(sources),
        curation_queue_items=len(queue),
    )
    (schema.REPORTS / "migration_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
