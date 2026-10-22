# Surface-rupture earthquake database

A literature-based database of surface-rupture earthquake metrics (slip, rupture length, off-fault deformation, shallow slip deficit, stress drop, ...). Every number is published in a study and stored with its provenance, source location, method, and uncertainty. Live observation tables are intentionally empty; contributors enter values manually using the Excel workbook.

```text
data/*.csv  ──(validate)──►  scripts/build.py  ──►  site/ (ignored build product)
													   └─► map · correlations · study comparison
```

## Quick start

Use Python 3.12 or newer. Reuse an existing virtual environment if available. Otherwise create and activate one:

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
```

Then install dependencies and run checks (use `python3` instead of `python` on macOS/Linux if that is your Python 3 command):

```bash
python -m pip install -r requirements.txt
python scripts/make_template.py --example
python scripts/ingest.py my_file.xlsx       # dry run; reports every issue by sheet and row
python scripts/validate.py                  # expect: OK: no new errors
python scripts/build.py                     # build site/; works from file://
python -m unittest discover -s tests -v
python tests/ui_smoke.py
```

## Architecture and files

`data/*.csv` are the canonical tables. `scripts/ingest.py` imports the single `INGESTION` worksheet defined by `scripts/workbook_spec.py`; related series rows share an `observation_group_id`. For a column-by-column explanation, see [docs/INGESTION_FIELDS.md](docs/INGESTION_FIELDS.md). `scripts/build.py` creates the ignored `site/` output and the three static interfaces. `fixtures/v7_migrated/` is unverified demo/test data only; it is not live data. See `docs/ARCHITECTURE.md`, `docs/INGESTION_PROTOCOL.md`, `docs/SCHEMA.md`, `docs/DECISIONS.md`, and `CONTRIBUTING.md`.

To build the fixture demo on macOS/Linux:

```bash
RUPTURE_DATA_DIR=fixtures/v7_migrated/data RUPTURE_BASELINES_DIR=fixtures/v7_migrated/baselines RUPTURE_REPORTS_DIR=/tmp/rep RUPTURE_SITE_DIR=/tmp/demo_site python scripts/build.py
```

In PowerShell, set the same `RUPTURE_*` variables with `$env:RUPTURE_DATA_DIR = "fixtures/v7_migrated/data"` (and corresponding paths for the other variables) before running `python scripts/build.py`.

