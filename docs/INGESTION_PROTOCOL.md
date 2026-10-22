# Ingestion protocol

## Rules (the importer enforces them)
1. **One row = one value that a publication prints** (text, table, supplement, machine-readable data).
2. **Never calculate.** No averaging, no unit juggling beyond conversion to the canonical unit (keep the printed form in `reported_text`), and **never derive OFD or SSD** from other measurements: ingest them only if the study publishes them, **as % fractions**. Min/mean/median/max of a published *array* are computed by the build, not by you.
3. **Provenance is mandatory**: `publication` (original study) and `source_location`. If you read it in a compilation, put the original study in `publication` and the compilation in `compiled_in`. The same study cited under spelling variants or with a different year is *one* publication: search the list and DOI first.
4. **Ambiguity must be resolved with fields**, not by adding duplicates: when one study gives several values for the same event/metric/statistic, distinguish them with `component`, `segment` or `model_id` (e.g. SSD for each slip model).
5. **Missing is empty**, never `0`, `-`, `NA`.
6. **Uncertainty**: choose `uncertainty_type` and give *positive offsets* `uncertainty_minus`, `uncertainty_plus`. If nothing is reported leave all empty (it is stored as `not_reported`). A published ± without a stated convention is `unspecified`, never guessed.
7. **Ranges and inequalities**: "113–140 km" → `value_range_low`, `value_range_high` (value empty). "<14 m" → `value`=14, `qualifier`=`<`. These are never turned into a number.
8. **Figures**: digitizing a figure is allowed only with `value_origin = digitized`, a `digitization_method` (software, axis calibration, panel) and a positive `digitization_unc`. It is shown with a distinct symbol and is independent of the paper's own uncertainty.
9. **Surface afterslip** (`surface_afterslip`, m) is its own metric: do not add it to coseismic slip.
10. **Different Mw for the same earthquake** are not different events: add them as `moment_magnitude` observations.

## The workbook
`templates/ingestion_template.xlsx` has **one main sheet, INGESTION: one row = one published value**. Its columns (defined once in `scripts/workbook_spec.py`, listed with descriptions in the FIELDS sheet) are grouped by coloured bands:

| Group | Columns |
|---|---|
| Identification and provenance | dataset_id, observation_group_id, source_row_id, **metric_id, target_id (earthquake), source_id (original study)**, compiled_in, **source_location**, value_origin, digitization_method, digitization_unc |
| Value | value, value_range_low/high, qualifier, unit, **statistic_type**, sample_count, component, segment, model_id, reported_text, derive_stats |
| Uncertainty | uncertainty_type, uncertainty_minus, uncertainty_plus, uncertainty_description, confidence_level |
| Location | spatial_representation, longitude, latitude, depth_m, horizontal/depth_location_uncertainty_m, coordinate_origin, coordinate_conversion_method, source_spatial_data, source_spatial_unit, source_reference_description |
| Method and comments | **method**, method_details, spatial_resolution, sensitivity_threshold(+unit), measurement_start/end, comments, quality_flag, quality_reason, verified_against |

Bold = always required; other fields are required only in the cases named in the header note (hover over a header) or optional. `record_id`, `submitted_by`, `submitted_on` and `review_status` are generated. Small side sheets, used only when something is missing from the dropdowns: NEW_EVENTS, NEW_PUBLICATIONS, EVENT_ALIASES. `templates/ingestion_example_filled.xlsx` shows every pattern with fictional values and **cannot be imported** (rows are marked `[EXAMPLE]`).

**Series.** Rows that share an `observation_group_id` and all have `statistic_type = individual` (two or more) are stored as one *series* (array) with their per-row values, offsets and positions; the build computes min/mean/median/max. Rows of a series must agree on event, metric, study, component, segment, model, unit, method, source_location, uncertainty_type and origin. Rows with the same group id but another statistic (e.g. the paper's own maximum) stay ordinary observations tagged with the group id; the paper's own value wins over a computed one.

**Uncertainty names.** `uncertainty_minus/plus` are positive offsets from the value (not the absolute bounds used internally by the plots). `uncertainty_type` accepts 1_sigma, 2_sigma, 95_ci, credible_interval, range, qualitative, unspecified, not_reported.

**Not (yet) supported:** `target_type` other than earthquake events (faults and fault sections are phase 2), `statistic_type = percentile`, `geometry_id`.

## Workflow
1. Open `templates/ingestion_template.xlsx` (regenerate with `make_template.py` after the registries change). Orange headers are required, yellow ones in some cases, blue ones optional.
2. New earthquake → `NEW_EVENTS`; other names for an existing one → `EVENT_ALIASES`; new paper → `NEW_PUBLICATIONS` (full reference + DOI or `no_doi_reason`).
3. Values → `INGESTION` (one row per value). Along-fault series: one row per measurement, same `observation_group_id`.
4. `python scripts/ingest.py file.xlsx` → read `reports/ingest_<file>.md`; fix every error (listed with sheet and row).
5. `python scripts/ingest.py file.xlsx --apply --submitter "Name (ORCID)"` (rolls back if validation fails).
6. `python scripts/validate.py && python scripts/build.py`, commit `data/`, open a pull request. CI re-validates and rebuilds.
7. A second person checks each value against the paper and runs `scripts/review.py` (status `reviewed_against_text|table`, `verified`). A reviewer can never be the submitter; reviewed rows must carry `reported_text`.

## What the importer rejects (examples)
unknown event/metric/publication · missing `source_location` or `method` · `value_origin = database_derived` · both value and range · range with only one end · uncertainty without `unc_type` or with negative offsets · qualitative uncertainty without a note · non-canonical unit · statistic not allowed for the metric · digitization without method/uncertainty · identical row already in the database or twice in the file · event that looks like an existing one (same name prefix within 2 days, unless `confirm_distinct=yes`) · publication whose DOI or id already exists.
Warnings (do not block): value outside the plausible range for the metric (check the unit); several individual values from one study (should they be distinguished?).

Legacy fixture note: pre-existing zero array offsets in `fixtures/v7_migrated/` are reported as `A004` warnings for source review. They are left unchanged because fixture values are unverified; new workbook imports reject zero offsets.
