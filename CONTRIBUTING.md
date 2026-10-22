# Contributing

## Adding data (contributors)
Follow `docs/INGESTION_PROTOCOL.md`. In short: fill the INGESTION sheet of the workbook → `python scripts/ingest.py file.xlsx` (dry run) → fix every reported row → `--apply --submitter "Name (ORCID)"` → open a pull request from a branch named `data/<your-name>-<topic>`.
Do **not** edit `data/*.csv` by hand unless you are fixing a registry (events, aliases, sources); the importer keeps files sorted and ids consistent.

## Reviewing (SURE database team, Milliner, Dolan, Reitman, ...)
- Open the PR; CI shows validation, tests and the rebuilt site.
- Check each new value against the paper (`source_location` tells you where). Then `python scripts/review.py --reviewer "Name" --status reviewed_against_table <ids>` (or `--list <event_id>` to see the unreviewed rows of an event).
- Disputes: `--status draft --comment "paper gives 3.1 m"` and leave a PR comment.

## Changing the code or schema
1. Schema changes: edit `scripts/schema.py`, regenerate `docs/SCHEMA.md` (`python scripts/make_schema_doc.py`), update `make_template.py` and `ingest.py`, add a test.
2. Never change an interface to compensate for bad data. Fix the data or the validator.
3. `python -m unittest discover -s tests` and `python tests/ui_smoke.py` must pass. The build must stay deterministic (same inputs → byte-identical `site/data.js`).
4. Dropping or merging records: run `validate.py --accept-counts` deliberately and explain why in the PR (the counts baseline is the protection against silent loss).

## Known-issues baseline
`baselines/known_issues.csv` lists legacy errors that are tolerated *only until fixed* (ratchet). New errors always fail CI. The live baseline is empty.
