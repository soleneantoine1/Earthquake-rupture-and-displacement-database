import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


class Sandbox:
    """A throw-away copy of the data (live or fixture) with its own reports/baselines/site dirs."""

    def __init__(self, source="fixture"):
        self.tmp = Path(tempfile.mkdtemp(prefix="rupture_test_"))
        src = ROOT / "fixtures" / "v7_migrated" if source == "fixture" else ROOT
        self.data, self.reports, self.baselines, self.site = (self.tmp / n for n in ("data", "reports", "baselines", "site"))
        shutil.copytree(src / "data", self.data)
        shutil.copytree(src / "baselines", self.baselines)
        self.reports.mkdir()
        self.env = dict(os.environ, RUPTURE_DATA_DIR=str(self.data), RUPTURE_REPORTS_DIR=str(self.reports),
                        RUPTURE_BASELINES_DIR=str(self.baselines), RUPTURE_SITE_DIR=str(self.site))

    def run(self, script, *args, cwd=None):
        return subprocess.run([PY, "-I", str(ROOT / "scripts" / script), *args], env=self.env, capture_output=True, text=True,
                              cwd=cwd or self.tmp)

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
