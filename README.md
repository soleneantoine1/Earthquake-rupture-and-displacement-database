# Surface-rupture earthquake database

# Authors: Solene Antoine (SCEC/USC), Ahmed Elbanna (SCEC/USC), Theo Bourdais (Caltech), and Roland Burgman (UC Berkeley)
# Created: 10/22/2026
# Last update: 10/22/2026

This tool is a literature-based database of metrics characterizing surface-rupturing earthquakes and associated deformation (slip, rupture length, off-fault deformation, shallow slip deficit, stress drop, etc). Metric values are extracted from peer-reviewed publications, and are stored in the database with their provenance, source location, method, and uncertainty. Contributors enter values manually using the Excel workbook. Values are plotted on three visual interfaces including: 1) a map that shows the global distribution of values for a given metric, 2) a 2D correlation plot tool to look at relations between two metrics, and 3) a tool that compares all published values for a similar metric.

```text
INGESTION workbook ──► scripts/ingest.py ──► data/*.csv ──► scripts/build.py ──► map · correlations · study comparison
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
