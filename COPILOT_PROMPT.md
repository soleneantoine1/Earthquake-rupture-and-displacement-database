# Prompt for VS Code Copilot (agent mode)

> Paste everything below the line into Copilot Chat (Agent mode) with this repository folder open. Use the strongest model available. Work in the order given. Ask me only where the text says **ASK**.

---

You are my engineering partner on a scientific database. Read this whole prompt, then `README.md`, `docs/ARCHITECTURE.md`, `docs/INGESTION_PROTOCOL.md`, `docs/SCHEMA.md`, `docs/DECISIONS.md` and `CONTRIBUTING.md` before changing anything.

## 1. What this is
A **literature-based database of surface-rupture earthquake metrics** (slip, rupture length, off-fault deformation (OFD), shallow slip deficit (SSD), stress drop, ...). Values come only from published studies and are entered **manually** by me and other contributors through an Excel workbook. Three things are needed: (1) a robust **database architecture**, (2) a strict **ingestion protocol and file**, (3) three **dynamic interfaces** (global event map, correlation explorer, study-to-study comparison) derived from my earlier prototype "v7".

**This folder is already a working reference implementation.** It passes `python -m unittest discover -s tests` (41 tests) and `python tests/ui_smoke.py`. Your job is **not to rewrite it**; it is to verify it, harden it, finish the items below, and publish it to GitHub through a reviewed pull request. If you think a design choice is wrong, say why and propose a change in the PR description rather than silently replacing it.

The earlier prototype failed because the same data lived in several places, fixes in one place broke another, records were lost or ingested twice, and uncertainties were stored inconsistently. Every rule below exists to prevent one of those failures.

## 2. Non-negotiable rules
Scientific
1. Every value is **published** by a study and carries `pub_ids` + `source_location`. If read from a compilation, the compilation goes in `compiled_in` and the original study in `pub_ids`. The interface shows the full reference **and DOI** for both.
2. **Never derive** OFD or SSD (or any high-level metric) from other measurements; they exist only as published `%` fractions (`off_fault_deformation_fraction`, `ssd_fraction`). The *only* computed values are min/mean/median/max of a **stored published array**, computed at build time, labelled `database_derived`, never stored in the tables, and suppressed if the same study reports that statistic itself.
3. **Uncertainty** = `unc_type` (what the paper means) + **positive offsets** `unc_minus`/`unc_plus`. Absolute bounds exist only in the build output. A published **range** (`value_lo`/`value_hi`) or inequality (`qualifier`) is never turned into a number or an uncertainty. **Figure digitization** is allowed only with `origin=figure_digitized`, a method, and a positive `digitization_unc`, shown with a distinct symbol and kept separate from the paper's uncertainty.
4. Missing = empty. **Never plot a missing/unparsed value as 0.**
5. One earthquake = one event. Different published Mw values are `moment_magnitude` observations; the build shows a Mw range. Events/publications are unique by id, alias, DOI; spelling or one-year variants are aliases/duplicates, not new rows. Publications are atomic (one paper per row).
6. No regression line in the correlation plot (explicit decision).
7. **Do not add, guess, extract or "fix" scientific values.** The live `data/observations.csv`, `arrays.csv`, `array_values.csv` stay **empty** (headers only). Test data live only in `fixtures/v7_migrated/` and are unverified.

Engineering
8. `data/*.csv` is the **single source of truth**; `site/` is a git-ignored build product. Pages must keep loading one shared `data.js` and `common.js` (no copies of data embedded in HTML; no per-page derived logic).
9. The build must stay **deterministic** (byte-identical `data.js`, `all_records.csv`, `estimates.geojson` for the same inputs).
10. A change that lowers any event x metric record count must fail the validator (`baselines/counts.csv`); never run `--accept-counts` or `--update-baseline` to make a failure go away without telling me.
11. Interfaces must work from `file://` and GitHub Pages (relative links, no server, no bundler), must list **all 29 metrics even when empty**, and must show an explanatory empty-state instead of crashing.
12. Pin CDN library versions (Leaflet 1.9.4, D3 7.9.0) or vendor them under `web_src/vendor/` with licences. No new runtime dependency without a reason in the PR.
13. Do not commit secrets, tokens, or personal data. Do not rewrite history or force-push.

## 3. Step 0: verify the starting point (report results, change nothing yet)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt playwright && playwright install chromium
python scripts/validate.py                  # expect: OK: no new errors
python -m unittest discover -s tests -v     # expect: 41 tests OK
python scripts/build.py                     # expect: 0 records, 100 events, 23 publications
python tests/ui_smoke.py                    # expect: passed
```
Then open `site/index.html` in a **real browser** (the smoke test stubs Leaflet, so the map tiles/markers have not been seen in a browser yet) and confirm: the map shows 77 grey markers and the banner "The database contains no observations yet"; Correlations and Study comparison load without console errors; all 29 metrics are selectable. Build the demo with the v7 fixture (command in README) and confirm the three pages show data, that clicking a point shows the provenance panel with the DOI link, and that "Download ... (CSV)" works. **Report every discrepancy before moving on.**

## 4. Step 1: GitHub setup
- **ASK me**: repository **owner**, **name**, and **visibility** (public/private). The repository I probably already have is `soleneantoine1/Earthquake-rupture-and-displacement-database`; confirm it or tell me what you would create. If it already has content, do not overwrite it: add this work on a branch and list what was already there.
- Create branch `foundation/database-architecture` (never commit to `main`). Use small, meaningful commits (Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `ci:`). Never force-push.
- If `git`/`gh` authentication is missing, **stop** and print the exact commands I should run (`gh auth login`, `git remote add origin ...`, `git push -u origin foundation/database-architecture`) instead of improvising.
- Open a **draft pull request** into `main` when Phase A is done; mark ready after CI is green.
- Enable GitHub Pages (source: GitHub Actions) only after I confirm the visibility (Pages on a private repo may need a paid plan; tell me if so).

## 5. Phase A: harden what exists (must finish before Phase B)
A1. **CI**: confirm `.github/workflows/ci.yml` runs on a clean runner (validate, unit tests, template freshness, build, UI smoke test, Pages deploy on `main`). Fix anything that fails there but passed locally. Add a job summary that prints the validator's counts.
A2. **Importer robustness** (`scripts/ingest.py`): add tests for (a) workbook with an extra/misspelled column, (b) Excel date cells in `event_date` and `measurement_start/end`, (c) numbers typed as text with a comma decimal ("3,2"), (d) `source_id` given as DOI, as `pub_id`, and as "Author et al. (year) [pub_id]" (the dropdown format), (e) a series pasted with 500 rows, (f) rows pasted with blank trailing lines or hidden/filtered rows, (g) two contributors adding different rows to the same event on different branches (merge must not conflict; ids are hashes), (h) `--apply` rollback when validation fails after merge. Fix bugs you find, minimal changes, each with a test.
A3. **Template**: the contributor workbook is deliberately simple: ONE main sheet `INGESTION` (one row per published value, columns grouped by coloured bands Identification / Value / Uncertainty / Location / Method, field definitions in `scripts/workbook_spec.py`), small side sheets `NEW_EVENTS`, `NEW_PUBLICATIONS`, `EVENT_ALIASES`, a `FIELDS` dictionary and a short `HOW TO`. Do not add sheets or merge the examples into it. Open `templates/ingestion_template.xlsx` and `templates/ingestion_example_filled.xlsx` in Excel and LibreOffice and check dropdowns, the frozen header, the hover notes on headers, the hidden `LISTS` sheet. Dropdown lists are generated from `data/`; verify a 100-event list and 29 metrics appear and that typing a free value gives a warning, not a block. Report layout problems; fix cosmetic ones. Never change a field name or meaning without updating the importer, tests and `docs/INGESTION_PROTOCOL.md`.
A4. **Series rule**: rows sharing `observation_group_id` with `statistic_type=individual` become one stored array (min/mean/median/max computed at build). Check this against the protocol text and tests; do not add a second way to enter arrays.
A5. **Validator**: review `scripts/validate.py` check list against `docs/INGESTION_PROTOCOL.md`; every rule in the protocol must have a check and a test. List any rule without one and add it.
A6. **Docs**: make sure the README quick start works verbatim on Windows, macOS and Linux (adjust commands; note `python3` vs `python`).

Acceptance for Phase A: CI green on the PR; all tests pass; no change to `site/` output on the fixture except where a bug was fixed (show the diff of `all_records.csv`).

## 6. Phase B: interface improvements (one PR each, after Phase A is merged)
Use `legacy/*_pre.txt` / `*_post.txt` (v7 pages) as the visual reference; keep their conventions (viridis ramp, symbol per statistic, side panel with provenance). Each item needs a Playwright check in `tests/ui_smoke.py`.
B1. **Map**: legend for categorical metrics; marker size by Mw (already) with Mw range in the tooltip; a "records exist but not plottable" style (dashed) is already present - verify in a real browser; link from the side panel to the comparison page for the same event/metric (`comparison.html#e=<event>&m=<metric>`).
B2. **Correlation**: pairing modes (selector): *across-study median per event* (current), *same study (both values from one publication)*, *all combinations*. Show the number of points and the number of events dropped, and why. **No regression line.**
B3. **Comparison**: group by publication with the full reference on hover; filter by statistic, review status, and `origin`; show `model_id`/`segment` in the row label when a study has several.
B4. **All pages**: keyboard-accessible controls, colour-blind-safe palette check, narrow-screen layout, print stylesheet.
B5. **Geometry layer** (design only, no data): propose a `geometries` table for along-strike traces/arrays using the `lat`/`lon` already stored in `array_values`; write the proposal in `docs/` and wait for my approval.

## 7. Acceptance checklist (tick in the PR description)
- [ ] `validate.py` OK; 41+ unit tests pass; UI smoke passes in CI.
- [ ] Live `data/observations.csv`, `arrays.csv`, `array_values.csv` contain headers only.
- [ ] Fixture demo: 1,895 records (979 reported + 916 computed), 100 events, 132 publications; the three pages render with no console errors.
- [ ] Re-importing the same workbook is rejected; importing a workbook with one bad row imports nothing.
- [ ] Ridgecrest check on the fixture: both Ridgecrest events have records (`test_ridgecrest_acceptance`).
- [ ] Determinism: two builds produce identical `data.js`.
- [ ] No value is plotted as 0 when missing; ranges/qualifiers are listed as "cannot be placed", not drawn as points (except the thick range bar on the comparison page).
- [ ] GitHub Pages deploys from `main` and the site opens at the Pages URL.
- [ ] README quick start verified on a clean clone.

## 8. What to report back to me
A short summary: what you verified, what you changed and why (one line per commit), anything you could not do, decisions you need from me, and the PR URL. Do not paste long logs; attach them as files if needed.

## 9. Things you must NOT do
- Do not fill the live tables with data, extract values from papers, or "complete" missing events/references from memory. Missing coordinates (23 events), dates (12) and full references are **curation tasks for me**, not for you.
- Do not replace the CSV-in-git model with a server/ORM, or the static pages with a framework, without a written proposal and my approval.
- Do not weaken a validator rule, baseline new errors, or accept count drops to get CI green.
- Do not add regression/fit lines, derived OFD/SSD, or midpoint values for ranges.
- Do not commit generated output (`site/`, `reports/*.md`).
