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


class EmptyLiveTests(unittest.TestCase):
    def test_live_database_builds_empty_and_valid(self):
        sb = Sandbox("live")
        try:
            r = sb.run("build.py")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            d = read_data_js(sb)
            self.assertEqual(len(d["records"]), 11)
            self.assertEqual(len(d["metrics"]), 31)
            self.assertEqual(len(d["events"]), 2)
            self.assertEqual({e["event_id"] for e in d["events"]}, {"Ridgecrest 1", "Ridgecrest 2"})
        finally:
            sb.cleanup()


if __name__ == "__main__":
    unittest.main()
