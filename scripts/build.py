#!/usr/bin/env python3
"""Deterministic build:  canonical CSV tables  ->  site/ (everything the interfaces and QGIS need).

  python scripts/build.py

Outputs (all regenerated, never edited by hand):
  site/data.js              window.DATA used by the three interfaces (one shared copy)
  site/rupture.sqlite       relational database (tables + views, incl. computed array statistics)
  site/estimates.geojson    spatial layer for QGIS
  site/all_records.csv      flat export: reported records + statistics computed from arrays

Rules enforced here:
  * min/mean/median/max are computed from arrays at build time and never stored in data/.
  * same inputs -> byte-identical outputs (no timestamps, sorted rows).
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema                                  # noqa: E402
from common import read_table, to_float        # noqa: E402

ARR_CTX = ["dataset_id", "group_id", "quality", "quality_reason", "confidence_level", "measurement_start", "measurement_end",
           "spatial_resolution", "sensitivity_threshold", "sensitivity_threshold_unit", "spatial_representation",
           "coordinate_origin", "coordinate_conversion_method", "source_spatial_unit", "source_reference_description"]
STAT_COLS = ["array_id", "statistic", "value", "n", "event_id", "metric_id", "pub_ids", "compiled_in", "component",
             "segment", "model_id", "unit", "source_location", "method", "calculation"] + ARR_CTX
RECORD_COLS = ["record_id", "target_id", "metric_id", "source_id", "statistic_type", "value", "unit", "uncertainty_lower",
               "uncertainty_upper", "uncertainty_type", "value_origin", "sample_count", "component", "calculation", "method",
               "method_details", "study_reference_full", "publication", "compiled_in_reference",
               "original_measurement_reference", "source_location", "database_location", "review_status", "flags", "comment",
               "value_lo", "value_hi", "range_type", "qualifier", "origin", "digitization_method", "digitization_unc",
               "model_id", "segment", "plottable", "value_num", "dataset_id", "group_id", "quality", "quality_reason",
               "confidence_level", "measurement_start", "measurement_end", "spatial_resolution", "sensitivity_threshold",
               "sensitivity_threshold_unit", "spatial_representation", "longitude", "latitude", "depth_m",
               "coordinate_origin", "coordinate_conversion_method", "source_spatial_data", "source_spatial_unit",
               "source_reference_description", "event_name", "event_date", "event_mw", "metric_name", "metric_value_type"]

CALC_TEXT = {
    "minimum": "MIN of published array values",
    "mean": "arithmetic mean of published array values",
    "median": "median of published array values",
    "maximum": "MAX of published array values",
}


def g(x):
    """float or None -> JSON friendly (round-trip safe)"""
    return None if x is None else float(x)


def display_value(r):
    """What the interfaces show / plot.  A plain number only when the study published a plain number."""
    vn, lo, hi = to_float(r["value_num"]), to_float(r["value_lo"]), to_float(r["value_hi"])
    if vn is not None and not r["qualifier"]:
        return vn
    if vn is not None:
        return f"{r['qualifier']}{vn:g}"
    if lo is not None and hi is not None:
        return f"{lo:g}–{hi:g}"
    return r["value_text"]


def bounds(r):
    """positive offsets -> absolute bounds used by the plots"""
    vn = to_float(r["value_num"])
    um, up = to_float(r["unc_minus"]), to_float(r["unc_plus"])
    if vn is None or (um is None and up is None):
        return None, None
    return (vn - um if um is not None else vn), (vn + up if up is not None else vn)


def load():
    return {n: read_table(n) for n in schema.FILES}


def compute_array_stats(tabs):
    arrays = tabs["arrays"].set_index("array_id")
    av = tabs["array_values"].copy()
    av["value"] = av["value"].astype(float)
    rows = []
    for aid, grp in av.groupby("array_id", sort=True):
        a = arrays.loc[aid]
        if a["derive_stats"] != "true":
            continue
        vals = grp.sort_values("idx", key=lambda s: s.astype(int))["value"].to_numpy(float)
        for stat, fn in (("minimum", np.min), ("mean", np.mean), ("median", np.median), ("maximum", np.max)):
            rows.append(dict(
                array_id=aid, statistic=stat, value=float(fn(vals)), n=len(vals),
                event_id=a["event_id"], metric_id=a["metric_id"], pub_ids=a["pub_ids"],
                compiled_in=a["compiled_in"], component=a["component"], segment=a["segment"],
                model_id=a["model_id"], unit=a["unit"], source_location=a["source_location"],
                method=a["method"], calculation=CALC_TEXT[stat], **{k: a[k] for k in ARR_CTX}))
    return pd.DataFrame(rows, columns=STAT_COLS)


def build_records(tabs, stats):
    ev = tabs["events"].set_index("event_id")
    mt = tabs["metrics"].set_index("metric_id")
    so = tabs["sources"].set_index("pub_id")

    def short(pids):
        return "; ".join(sorted(so.loc[p, "citation_short"] for p in pids.split("|") if p))

    def full(pids):
        return "; ".join(sorted((so.loc[p, "citation_full"] or so.loc[p, "citation_short"]) for p in pids.split("|") if p))

    def common(eid, mid):
        e, m = ev.loc[eid], mt.loc[mid]
        return dict(event_name=e["event_name"], event_date=e["event_date"] or None, event_mw=to_float(e["mw"]),
                    metric_name=m["display_name"], metric_value_type=m["value_type"])

    recs = []
    for _, r in tabs["observations"].iterrows():
        lo, hi = bounds(r)
        pids = r["pub_ids"]
        comp_ref = (so.loc[r["compiled_in"], "citation_full"] or so.loc[r["compiled_in"], "citation_short"]) if r["compiled_in"] else None
        rec = dict(
            record_id=r["obs_id"], target_id=r["event_id"], metric_id=r["metric_id"], source_id=pids,
            statistic_type=r["statistic"], value=display_value(r), unit=r["unit"] or None,
            uncertainty_lower=g(lo), uncertainty_upper=g(hi), uncertainty_type=r["unc_type"],
            value_origin="reported", sample_count=to_float(r["n"]), component=r["component"] or r["segment"] or None,
            calculation=None, method=r["method"], method_details=r["method_details"],
            study_reference_full=full(pids), publication=short(pids),
            compiled_in_reference=comp_ref,
            original_measurement_reference=short(pids) if comp_ref else None,
            source_location=r["source_location"],
            database_location=f"observations.csv, {r['obs_id']}" + (f"; source location: {r['source_location']}" if r["source_location"] else ""),
            review_status=r["review_status"], flags=r["flags"] or None, comment=r["comment"] or None,
            value_lo=to_float(r["value_lo"]), value_hi=to_float(r["value_hi"]), range_type=r["range_type"] or None,
            qualifier=r["qualifier"] or None, origin=r["origin"], digitization_method=r["digitization_method"] or None,
            digitization_unc=to_float(r["digitization_unc"]), model_id=r["model_id"] or None, segment=r["segment"] or None,
            value_num=to_float(r["value_num"]),
            dataset_id=r["dataset_id"] or None, group_id=r["group_id"] or None, quality=r["quality"] or None,
            quality_reason=r["quality_reason"] or None, confidence_level=to_float(r["confidence_level"]),
            measurement_start=r["measurement_start"] or None, measurement_end=r["measurement_end"] or None,
            spatial_resolution=r["spatial_resolution"] or None, sensitivity_threshold=to_float(r["sensitivity_threshold"]),
            sensitivity_threshold_unit=r["sensitivity_threshold_unit"] or None,
            spatial_representation=r["spatial_representation"] or None, longitude=to_float(r["longitude"]),
            latitude=to_float(r["latitude"]), depth_m=to_float(r["depth_m"]), coordinate_origin=r["coordinate_origin"] or None,
            coordinate_conversion_method=r["coordinate_conversion_method"] or None,
            source_spatial_data=r["source_spatial_data"] or None, source_spatial_unit=r["source_spatial_unit"] or None,
            source_reference_description=r["source_reference_description"] or None,
            plottable=isinstance(display_value(r), float) or (mt.loc[r["metric_id"], "value_type"] == "categorical"))
        rec.update(common(r["event_id"], r["metric_id"]))
        recs.append(rec)
    # computed statistics: skip when the same study already reports that statistic (reported wins)
    reported_keys = {(r["event_id"], r["metric_id"], r["pub_ids"], r["statistic"], r["component"], r["segment"])
                     for _, r in tabs["observations"].iterrows()}
    skipped = 0
    for _, s in stats.iterrows():
        if (s["event_id"], s["metric_id"], s["pub_ids"], s["statistic"], s["component"], s["segment"]) in reported_keys:
            skipped += 1
            continue
        pids = s["pub_ids"]
        comp_ref = (so.loc[s["compiled_in"], "citation_full"] or so.loc[s["compiled_in"], "citation_short"]) if s["compiled_in"] else None
        rec = dict(
            record_id=f"{s['array_id']}:{s['statistic'][:3]}", target_id=s["event_id"], metric_id=s["metric_id"],
            source_id=pids, statistic_type=s["statistic"], value=float(s["value"]), unit=s["unit"] or None,
            uncertainty_lower=None, uncertainty_upper=None, uncertainty_type="not_propagated",
            value_origin="database_derived", sample_count=float(s["n"]), component=s["component"] or s["segment"] or None,
            calculation=s["calculation"], method=s["method"], method_details="statistic computed at build time from the stored array",
            study_reference_full=full(pids), publication=short(pids), compiled_in_reference=comp_ref,
            original_measurement_reference=short(pids) if comp_ref else None,
            source_location=s["source_location"],
            database_location=f"array_values.csv, {s['array_id']}; source location: {s['source_location']}",
            review_status="draft", flags=None, comment=None, value_lo=None, value_hi=None, range_type=None,
            qualifier=None, origin="reported", digitization_method=None, digitization_unc=None,
            model_id=s["model_id"] or None, segment=s["segment"] or None, plottable=True, value_num=float(s["value"]),
            **{k: (to_float(s[k]) if k in ("confidence_level", "sensitivity_threshold") else (s[k] or None)) for k in ARR_CTX},
            longitude=None, latitude=None, depth_m=None, source_spatial_data=None)
        rec.update(common(s["event_id"], s["metric_id"]))
        recs.append(rec)
    recs.sort(key=lambda r: (r["target_id"], r["metric_id"], r["statistic_type"], str(r["publication"]), str(r["component"] or ""), r["record_id"]))
    return recs, skipped


def build_events(tabs, recs):
    mw = {}
    for r in recs:
        if r["metric_id"] == "moment_magnitude" and isinstance(r["value"], float):
            mw.setdefault(r["target_id"], []).append(r["value"])
    n = pd.Series([r["target_id"] for r in recs], dtype=object).value_counts()
    aliases = tabs["event_aliases"].groupby("event_id").alias.apply(list).to_dict()
    out = []
    for _, e in tabs["events"].iterrows():
        eid = e["event_id"]
        vals = mw.get(eid, [])
        rng = None
        if vals:
            lo, hi = min(vals), max(vals)
            rng = f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g}"
        out.append(dict(
            event_id=eid, event_name=e["event_name"], event_date=e["event_date"] or None, origin_time=None,
            mw=to_float(e["mw"]), mw_range=rng, hypocenter_latitude=to_float(e["latitude"]),
            hypocenter_longitude=to_float(e["longitude"]), hypocenter_depth_km=to_float(e["hypocenter_depth_km"]),
            centroid_depth_km=to_float(e["centroid_depth_km"]), mechanism=e["mechanism"] or None,
            region=e["region"] or None, coordinate_source=e["coordinate_source"] or None,
            sequence_id=e["sequence_id"] or None, aliases=sorted(aliases.get(eid, [])),
            n_records=int(n.get(eid, 0))))
    return out


def build_metrics(tabs, recs):
    used = {r["metric_id"] for r in recs}
    out = []
    for _, m in tabs["metrics"].iterrows():
        out.append(dict(
            metric_id=m["metric_id"], display_name=m["display_name"], category=m["category"],
            value_type=m["value_type"], canonical_unit=m["canonical_unit"] or None, plot_eligible=1,
            distribution_policy=m["distribution_policy"], definition_source=m["definition_source"],
            populated=m["metric_id"] in used))
    return out


def content_hash():
    h = hashlib.sha1()
    for name in sorted(schema.FILES):
        h.update(schema.FILES[name].read_bytes())
    return h.hexdigest()[:10]


def write_sqlite(path, tabs, stats, recs):
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    numeric = {"observations": ["value_num", "value_lo", "value_hi", "n", "unc_minus", "unc_plus"],
               "events": ["mw", "latitude", "longitude", "hypocenter_depth_km", "centroid_depth_km"],
               "metrics": ["plausible_min", "plausible_max"], "arrays": ["n_values"],
               "array_values": ["idx", "value", "unc_minus", "unc_plus", "lat", "lon"]}
    for name, df in tabs.items():
        d = df.copy()
        for c in numeric.get(name, []):
            d[c] = d[c].map(to_float)
        d.to_sql(name, con, index=False)
    st = stats.copy()
    st.to_sql("array_stats", con, index=False)
    con.executescript("""
    CREATE INDEX idx_obs_event_metric ON observations(event_id, metric_id);
    CREATE INDEX idx_arr_event_metric ON arrays(event_id, metric_id);
    CREATE INDEX idx_av_array ON array_values(array_id);
    CREATE VIEW event_summary AS
      SELECT e.event_id, e.event_name, e.event_date, e.mw, e.latitude, e.longitude,
             (SELECT MIN(value_num) FROM observations o WHERE o.event_id=e.event_id AND o.metric_id='moment_magnitude') AS mw_min,
             (SELECT MAX(value_num) FROM observations o WHERE o.event_id=e.event_id AND o.metric_id='moment_magnitude') AS mw_max,
             (SELECT COUNT(*) FROM observations o WHERE o.event_id=e.event_id) AS n_observations,
             (SELECT COUNT(*) FROM arrays a WHERE a.event_id=e.event_id) AS n_arrays
      FROM events e;
    CREATE VIEW metric_coverage AS
      SELECT m.metric_id, m.display_name,
             (SELECT COUNT(*) FROM observations o WHERE o.metric_id=m.metric_id) AS n_observations,
             (SELECT COUNT(*) FROM arrays a WHERE a.metric_id=m.metric_id) AS n_arrays,
             (SELECT COUNT(DISTINCT event_id) FROM (SELECT event_id FROM observations WHERE metric_id=m.metric_id
                                                    UNION SELECT event_id FROM arrays WHERE metric_id=m.metric_id)) AS n_events
      FROM metrics m;
    """)
    flat = pd.DataFrame([{k: (None if isinstance(v, (list, dict)) else v) for k, v in r.items()} for r in recs],
                        columns=RECORD_COLS)
    flat.to_sql("all_records", con, index=False)
    con.commit()
    con.close()


def write_geojson(path, recs, events):
    ev = {e["event_id"]: e for e in events}
    feats = []
    for r in recs:
        e = ev[r["target_id"]]
        if e["hypocenter_longitude"] is None or e["hypocenter_latitude"] is None:
            continue
        props = {k: r[k] for k in ("record_id", "target_id", "event_name", "event_date", "metric_id", "metric_name",
                                   "statistic_type", "value", "unit", "uncertainty_lower", "uncertainty_upper",
                                   "value_origin", "component", "publication", "compiled_in_reference",
                                   "source_location", "method", "review_status")}
        feats.append(dict(type="Feature", properties=props,
                          geometry=dict(type="Point", coordinates=[e["hypocenter_longitude"], e["hypocenter_latitude"]])))
    path.write_text(json.dumps(dict(type="FeatureCollection", features=feats), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf8")
    return len(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()
    if not args.skip_validate:
        r = subprocess.run([sys.executable, "-I", str(Path(__file__).parent / "validate.py"), "--quiet"])
        if r.returncode != 0:
            raise SystemExit("build aborted: validation failed (see above)")
    tabs = load()
    stats = compute_array_stats(tabs)
    recs, skipped = build_records(tabs, stats)
    events = build_events(tabs, recs)
    metrics = build_metrics(tabs, recs)
    sources = [{k: s[k] for k in ("pub_id", "citation_short", "citation_full", "doi", "kind")}
               for s in tabs["sources"].to_dict("records")]
    h = content_hash()
    schema.SITE.mkdir(exist_ok=True)
    data = dict(version=f"data-{h}", events=events, metrics=metrics, records=recs, sources=sources,
                build=dict(hash=h, records=len(recs), reported=sum(r["value_origin"] == "reported" for r in recs),
                           computed_from_arrays=sum(r["value_origin"] != "reported" for r in recs),
                           events=len(events), publications=len(sources),
                           computed_skipped_because_reported=skipped))
    (schema.SITE / "data.js").write_text(
        "window.DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + ";\n", encoding="utf8")
    web = schema.ROOT / "web_src"
    if web.is_dir():
        for f in sorted(web.iterdir()):
            if f.is_file():
                shutil.copy(f, schema.SITE / f.name)
    write_sqlite(schema.SITE / "rupture.sqlite", tabs, stats, recs)
    nfeat = write_geojson(schema.SITE / "estimates.geojson", recs, events)
    flat = pd.DataFrame([{k: v for k, v in r.items() if not isinstance(v, (list, dict))} for r in recs],
                        columns=RECORD_COLS)
    flat.to_csv(schema.SITE / "all_records.csv", index=False, lineterminator="\n")
    print(json.dumps(dict(data["build"], geojson_features=nfeat), indent=2))


if __name__ == "__main__":
    main()
