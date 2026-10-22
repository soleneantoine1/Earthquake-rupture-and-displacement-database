# Architecture

## Why this design (what went wrong in v7)
v7 stored the same information in several places (SQLite, three embedded copies of the data in the HTML pages, a spreadsheet) and the pages carried their own derived logic. Any fix in one place broke another; records were lost or duplicated silently; uncertainties were stored in mixed conventions. The new design removes each cause:

| Problem | Mechanism that prevents it |
|---|---|
| Fix here breaks there | **One source of truth** (`data/*.csv`). Everything else is a deterministic build product; the three pages load one shared `data.js` and one `common.js`. |
| Data silently disappear | **Count-regression gate**: `baselines/counts.csv` holds the number of records per event×metric. The validator fails if any count drops unless someone explicitly runs `--accept-counts`. v7 migration has a **conservation ledger** (every one of the 1,942 v7 records has exactly one fate). |
| Data ingested twice | Observation ids are a hash of the scientific key (`DUPLICATE_KEY`): the same value entered twice gets the same id and is rejected (D001). Publications are unique by DOI and by pub_id; events by id and alias (E004 flags look-alikes). |
| Uncertainty ambiguous | `unc_type` (what it means) + POSITIVE offsets `unc_minus/unc_plus`. The build converts to absolute bounds. Published ranges and figure-digitization error are stored in separate columns and never mixed with it. |
| Derived numbers mistaken for data | Only min/mean/median/max of a *stored array* are computed, **at build time**, flagged `database_derived`. If the same study reports the statistic itself, the reported value wins. OFD and SSD are ingested only as published % fractions and never derived. |

## Layers
1. **Canonical tables** (`data/`): events, event_aliases, metrics, sources, observations, arrays, array_values. Plain CSV, fixed column order, sorted by primary key, LF endings → readable git diffs, mergeable PRs.
2. **Validation** (`scripts/validate.py`): schema, vocabularies, foreign keys, duplicates, conflicts, uncertainty rules, array rules, counts. Known legacy errors can be *baselined* (ratchet: they may only go down); warnings never block.
3. **Ingestion** (`scripts/ingest.py` + the one-sheet INGESTION workbook; fields in `scripts/workbook_spec.py`): contributor-facing; resolves events/publications by id, alias, DOI or label; reports problems by sheet and row; all-or-nothing apply with automatic rollback.
4. **Build** (`scripts/build.py`): validates, then writes `site/`: `data.js`, `rupture.sqlite` (tables + views `event_summary`, `metric_coverage`, `all_records`), `estimates.geojson` (QGIS), `all_records.csv`.
5. **Interfaces** (`web_src/`): static pages, no server, work from `file://` and GitHub Pages.

## Provenance model
Each observation names the **original study** (`pub_ids`, pipe-separated if several) and, if it was read from a compilation, the **compilation** (`compiled_in`). The interfaces show the full reference and DOI of both, the source location (page/table/figure/supplement), method, `n`, uncertainty with its definition, review status, and where the row is stored.

## Identifiers
- Events: `event:<slug><year>` for new events; v7 ids (`sure:19920628`, …) are kept. Old ids/spellings live in `event_aliases.csv` (`alias_type` = `legacy_id` | `name_variant`). Merging two events requires an alias row with a `reason`.
- Publications: `<surname>_<year>` (atomic: one paper per row, never "A; B" labels). Compilations and agencies (USGS, GCMT, ISC-GEM, SURE 2.0, …) are rows with `kind` ≠ `publication`.
- Observations `O` + 12 hex, arrays `A` + 12 hex (hash of scientific key); legacy `R0000123` / `A0033` are kept.

## Different published magnitudes for one earthquake
One event, one preferred `mw` in `events.csv`; every other published Mw is an observation of metric `moment_magnitude`. The build reports `mw_range` (e.g. "7.3–7.6") and the interfaces show it.

## Environment overrides
`RUPTURE_DATA_DIR`, `RUPTURE_REPORTS_DIR`, `RUPTURE_BASELINES_DIR`, `RUPTURE_SITE_DIR` redirect the scripts (used by tests and the fixture demo).

## Phase 2 (designed for, not built)
- Fault and fault-section records (`target_type` fault / fault_section: slip rates, cumulative displacement) through a `faults` table; phase 1 holds earthquake events only.
- `percentile` statistics (needs a percentile-level column).
- Correlation pairing modes (same study / same component / all combinations) in addition to the across-study median.
- A `geometries` table for along-strike spatial layers (array lat/lon are already stored).
- A staging area with a reviewer UI. Today the pull request *is* the review; `review.py` records decisions.
