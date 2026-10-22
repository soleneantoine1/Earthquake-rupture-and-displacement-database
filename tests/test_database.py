import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, Sandbox  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import schema  # noqa: E402


def load(sb, name):
    return pd.read_csv(sb.data / f"{name}.csv", dtype=str, keep_default_na=False)


def read_data_js(sb):
    t = (sb.site / "data.js").read_text(encoding="utf8")
    return json.loads(t[len("window.DATA="):].rstrip().rstrip(";"))


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb = Sandbox("fixture")
        r = cls.sb.run("build.py")
        assert r.returncode == 0, r.stdout + r.stderr
        cls.data = read_data_js(cls.sb)

    @classmethod
    def tearDownClass(cls):
        cls.sb.cleanup()

    def test_validator_clean_against_baseline(self):
        r = self.sb.run("validate.py", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_build_is_deterministic(self):
        other = Sandbox("fixture")
        try:
            self.assertEqual(other.run("build.py").returncode, 0)
            for f in ("data.js", "all_records.csv", "estimates.geojson"):
                self.assertEqual((self.sb.site / f).read_bytes(), (other.site / f).read_bytes(), f)
        finally:
            other.cleanup()

    def test_array_statistics_match_independent_recomputation(self):
        av, ar = load(self.sb, "array_values"), load(self.sb, "arrays")
        recs = {r["record_id"]: r for r in self.data["records"]}
        checked = 0
        for _, a in ar[ar.derive_stats == "true"].iterrows():
            vals = av[av.array_id == a.array_id].value.astype(float).to_numpy()
            for stat, fn in (("minimum", np.min), ("mean", np.mean), ("median", np.median), ("maximum", np.max)):
                rid = f"{a.array_id}:{stat[:3]}"
                if rid in recs:
                    self.assertAlmostEqual(recs[rid]["value"], float(fn(vals)), places=9, msg=rid)
                    checked += 1
        self.assertGreater(checked, 500)

    def test_computed_stats_are_never_stored(self):
        obs = load(self.sb, "observations")
        arrays = load(self.sb, "arrays")
        computed = {r["record_id"] for r in self.data["records"] if r["value_origin"] == "database_derived"}
        self.assertTrue(computed)
        self.assertFalse(computed & set(obs.obs_id))
        self.assertFalse(any(rid.split(":")[0] not in set(arrays.array_id) for rid in computed))

    def test_ofd_ssd_only_as_fractions(self):
        ids = set(load(self.sb, "metrics").metric_id)
        self.assertNotIn("off_fault_deformation_absolute", ids)
        self.assertNotIn("ssd_absolute", ids)
        for m in ("off_fault_deformation_fraction", "ssd_fraction"):
            self.assertIn(m, ids)
        mt = load(self.sb, "metrics").set_index("metric_id")
        self.assertEqual(mt.loc["off_fault_deformation_fraction", "canonical_unit"], "%")

    def test_uncertainty_offsets_positive_and_bounds_consistent(self):
        obs = load(self.sb, "observations")
        for c in ("unc_minus", "unc_plus"):
            v = pd.to_numeric(obs[c], errors="coerce").dropna()
            self.assertTrue((v >= 0).all(), c)
        for r in self.data["records"]:
            if r["value_origin"] == "reported" and isinstance(r["value"], float):
                if r["uncertainty_lower"] is not None:
                    self.assertLessEqual(r["uncertainty_lower"], r["value"] + 1e-9)
                if r["uncertainty_upper"] is not None:
                    self.assertGreaterEqual(r["uncertainty_upper"], r["value"] - 1e-9)

    def test_ranges_and_qualifiers_are_not_numbers(self):
        for r in self.data["records"]:
            if r["value_lo"] is not None or r["qualifier"]:
                self.assertFalse(isinstance(r["value"], float), r["record_id"])
                self.assertFalse(r["plottable"], r["record_id"])

    def test_every_event_and_metric_listed_even_if_empty(self):
        self.assertEqual(len(self.data["metrics"]), 29)
        self.assertEqual(len(self.data["events"]), len(load(self.sb, "events")))

    def test_migration_ledger_conserves_every_v7_record(self):
        led = pd.read_csv(ROOT / "fixtures/v7_migrated/reports/migration_ledger.csv", dtype=str, keep_default_na=False)
        self.assertEqual(len(led), 1942)
        self.assertEqual(led.legacy_record_id.nunique(), 1942)

    def test_no_duplicate_events_or_publications(self):
        ev, so = load(self.sb, "events"), load(self.sb, "sources")
        self.assertEqual(ev.event_id.is_unique, True)
        dois = so[so.doi != ""].doi.str.lower()
        self.assertTrue(dois.is_unique)
        aliases = load(self.sb, "event_aliases")
        self.assertTrue(set(aliases.event_id) <= set(ev.event_id))
        self.assertFalse(set(aliases.alias) & set(ev.event_id))

    def test_ridgecrest_acceptance(self):
        ev = {e["event_id"]: e for e in self.data["events"]}
        ridge = [e for e in ev.values() if "idgecrest" in e["event_name"]]
        self.assertGreaterEqual(len(ridge), 2)
        for e in ridge:
            self.assertGreater(e["n_records"], 0, e["event_name"])


class ValidatorGuards(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox("fixture")

    def tearDown(self):
        self.sb.cleanup()

    def _write(self, name, df):
        df.to_csv(self.sb.data / f"{name}.csv", index=False, lineterminator="\n")

    def test_new_duplicate_observation_fails(self):
        obs = load(self.sb, "observations")
        row = obs[(obs.value_num != "") & (obs.qualifier == "")].iloc[0].copy()
        row["obs_id"] = "O" + "0" * 12
        self._write("observations", pd.concat([obs, row.to_frame().T], ignore_index=True))
        r = self.sb.run("validate.py", "--quiet")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("D001", r.stdout + (self.sb.reports / "validation_report.csv").read_text())

    def test_count_regression_fails(self):
        obs = load(self.sb, "observations")
        self._write("observations", obs.iloc[:-30])
        r = self.sb.run("validate.py", "--quiet")
        self.assertEqual(r.returncode, 1)
        self.assertIn("C001", r.stdout + (self.sb.reports / "validation_report.csv").read_text())

    def test_unknown_event_fails(self):
        obs = load(self.sb, "observations")
        obs.loc[obs.index[0], "event_id"] = "event:doesnotexist"
        self._write("observations", obs)
        self.assertEqual(self.sb.run("validate.py", "--quiet").returncode, 1)

    def test_negative_uncertainty_fails(self):
        obs = load(self.sb, "observations")
        i = obs.index[obs.unc_minus != ""][0]
        obs.loc[i, "unc_minus"] = "-1"
        self._write("observations", obs)
        self.assertEqual(self.sb.run("validate.py", "--quiet").returncode, 1)

    def test_negative_array_uncertainty_fails(self):
        values = load(self.sb, "array_values")
        i = values.index[values.unc_minus != ""][0]
        values.loc[i, "unc_minus"] = "-1"
        self._write("array_values", values)
        result = self.sb.run("validate.py", "--quiet")
        self.assertEqual(result.returncode, 1)
        self.assertIn("A003", (self.sb.reports / "validation_report.csv").read_text())

    def test_qualitative_array_uncertainty_requires_note(self):
        arrays = load(self.sb, "arrays")
        arrays.loc[arrays.index[0], "unc_type"] = "qualitative"
        arrays.loc[arrays.index[0], "unc_note"] = ""
        self._write("arrays", arrays)
        result = self.sb.run("validate.py", "--quiet")
        self.assertEqual(result.returncode, 1)
        self.assertIn("qualitative array uncertainty needs unc_note", (self.sb.reports / "validation_report.csv").read_text())

    def test_legacy_zero_array_offsets_are_reported_for_review(self):
        result = self.sb.run("validate.py", "--quiet")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = pd.read_csv(self.sb.reports / "validation_report.csv", dtype=str, keep_default_na=False)
        self.assertIn("A004", set(report.code))

    def test_figure_digitization_requires_declaration(self):
        obs = load(self.sb, "observations")
        obs.loc[obs.index[0], "origin"] = "figure_digitized"
        self._write("observations", obs)
        self.assertEqual(self.sb.run("validate.py", "--quiet").returncode, 1)


class EmptyLiveTests(unittest.TestCase):
    def test_live_database_builds_empty_and_valid(self):
        sb = Sandbox("live")
        try:
            r = sb.run("build.py")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            d = read_data_js(sb)
            self.assertEqual(d["records"], [])
            self.assertEqual(len(d["metrics"]), 29)
            self.assertGreater(len(d["events"]), 50)
        finally:
            sb.cleanup()


if __name__ == "__main__":
    unittest.main()
