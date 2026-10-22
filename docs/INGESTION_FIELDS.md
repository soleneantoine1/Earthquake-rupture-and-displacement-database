# INGESTION worksheet field guide

This guide explains the contributor-facing columns in the `INGESTION` worksheet. The field names and their order are defined in [`scripts/workbook_spec.py`](../scripts/workbook_spec.py); keep them unchanged in workbooks. Each row represents one value published for an earthquake. Use empty cells for missing information—never enter `0`, `NA`, or `-` to mean missing.

**Requirement labels:** **Required** means the importer always expects a value. **When applicable** means it is required only for the circumstance described. **Optional** means it can be left blank. Dropdowns suggest controlled values; some fields accept free text.

## Identification and provenance

| Column | Requirement | What it means |
|---|---|---|
| `dataset_id` | Optional | Identifies the particular dataset containing the value, such as a supplement file or repository dataset. Use the same identifier for related values from that dataset. |
| `observation_group_id` | Optional | Your label for related rows. Two or more rows with the same label and `statistic_type=individual` are stored as one series; other statistics remain separate observations. |
| `source_row_id` | Optional | The row number, record identifier, or other locator in the original source table. It helps a reviewer find the value again. |
| `metric_id` | Required | The controlled metric being reported, selected from the metric list (for example, `surface_fault_slip`). |
| `target_id` | Required | The earthquake the value describes. Select the canonical event; if it is missing, add it in `NEW_EVENTS`, or use `EVENT_ALIASES` for another name of an existing event. |
| `source_id` | Required | The original publication that reports the value. If the value was found in a compilation, keep the original study here and identify the compilation in `compiled_in`. |
| `compiled_in` | Optional | The compilation, database, or review from which you obtained the value, if applicable. It does not replace the original study in `source_id`. |
| `source_location` | Required | The precise place to verify the value, such as a page, table and row, figure panel, supplement file, or dataset field. |
| `value_origin` | Optional | Whether the value is reported in text/table/data or digitized from a figure; blank defaults to `reported`. Do not enter `database_derived`: the build computes permitted statistics from series. |
| `digitization_method` | When applicable | For a figure-digitized value, describe the software and procedure, including axis calibration and figure panel as appropriate. |
| `digitization_unc` | When applicable | Positive reading uncertainty introduced by digitizing, in the value's unit. Keep it separate from the publication's scientific uncertainty. |

## Value

| Column | Requirement | What it means |
|---|---|---|
| `value` | When applicable | The published number in the metric's canonical unit, or the published category for categorical metrics. Leave blank for a range-only value; never invent a midpoint. |
| `value_range_low` | Optional | The lower endpoint when the study publishes a range instead of a single value. Enter it together with `value_range_high`. |
| `value_range_high` | Optional | The upper endpoint of a published range. This is a range bound, not an uncertainty estimate. |
| `qualifier` | Optional | A published inequality or approximation marker (`<`, `>`, or `~`) attached to `value`. Do not convert it into an exact measurement. |
| `unit` | When applicable | The unit used for the value. Leave blank to use the metric's canonical unit; values in other units must be converted and the printed form retained in `reported_text`. |
| `statistic_type` | Required | What the paper reports: `individual`, `minimum`, `mean`, `median`, `maximum`, or `category` for categorical metrics. |
| `sample_count` | Optional | Number of measurements represented by a reported summary statistic, when the source provides it. |
| `component` | When applicable | The displacement component or measurement type specified by the study, such as strike-slip, vertical/throw, or net slip. |
| `segment` | Optional | The fault segment, strand, or sub-event to which the value applies. Use it to distinguish values reported for different parts of a rupture. |
| `model_id` | Optional | The name or identifier of the slip model, dataset, or solution associated with the value. Use it to distinguish multiple results from one publication. |
| `reported_text` | Optional | The value exactly as printed when it needs context, parsing, or unit conversion (for example, `320 cm` or `3.2 +0.5/-0.3 m`). |
| `derive_stats` | Optional | For a series, `yes` (the default) allows the build to compute min/mean/median/max; `no` keeps the series without those summaries. Never enter computed summary values as published observations. |

## Uncertainty

| Column | Requirement | What it means |
|---|---|---|
| `uncertainty_type` | When applicable | Describes what the publication's uncertainty means, such as `1_sigma`, `95_ci`, `credible_interval`, `qualitative`, or `unspecified`. Use `not_reported` when the paper provides no uncertainty. |
| `uncertainty_minus` | When applicable | Positive offset below the central value: the lower bound is `value - uncertainty_minus`. Enter a positive magnitude, not a signed value or an absolute bound. |
| `uncertainty_plus` | When applicable | Positive offset above the central value: the upper bound is `value + uncertainty_plus`. For symmetric uncertainty, enter the same positive offset in both minus and plus columns. |
| `uncertainty_description` | When applicable | A short explanation of qualitative uncertainty or an unusual uncertainty definition. It is required when `uncertainty_type` is `qualitative`. |
| `confidence_level` | Optional | The stated confidence or credible level as a percentage in `(0, 100]`, such as `95`. Do not infer a level that the publication does not give. |

## Location

| Column | Requirement | What it means |
|---|---|---|
| `spatial_representation` | Optional | Describes the spatial form or scale represented, such as `event_summary`, `point`, `profile`, `line`, or `grid`. |
| `longitude` | When applicable | WGS84 longitude in decimal degrees for the measurement or summary. For a series, enter a value on each row only when the source provides or supports that position. |
| `latitude` | When applicable | WGS84 latitude in decimal degrees for the measurement or summary. Provide it together with longitude. |
| `depth_m` | Optional | Representative measurement depth in metres, if published or otherwise supported by the source. |
| `horizontal_location_uncertainty_m` | Optional | Reported or documented horizontal positional uncertainty in metres. |
| `depth_location_uncertainty_m` | Optional | Reported or documented depth uncertainty in metres. |
| `coordinate_origin` | When applicable | States whether coordinates were published directly (`source`) or converted from another location measure (`converted`). Required when longitude or latitude is supplied. |
| `coordinate_conversion_method` | When applicable | Explains how source location information was converted to coordinates. Required when `coordinate_origin=converted`. |
| `source_spatial_data` | Optional | The original spatial measure as published, such as distance along strike. For a series, enter the source position on each applicable row. |
| `source_spatial_unit` | When applicable | Unit for `source_spatial_data`, such as `km`. Include it whenever source spatial data is provided and for coordinate conversions. |
| `source_reference_description` | When applicable | Defines the origin and reference direction or frame for a source position (for example, distance from the southern end of a rupture). Required for converted coordinates. |

## Method and comments

| Column | Requirement | What it means |
|---|---|---|
| `method` | Required | Broad measurement or analysis method used to obtain the value, such as field mapping, InSAR, GNSS, seismic analysis, or joint inversion. The dropdown is a guide; descriptive free text is allowed. |
| `method_details` | Optional | Short details about processing, instruments, model assumptions, or measurement choices that help interpret the value. |
| `spatial_resolution` | Optional | The smallest spatial scale resolved by the measurement, written with its unit (for example, `30 m`). |
| `sensitivity_threshold` | Optional | The numeric minimum sensitivity threshold reported for the method. If provided, also enter `sensitivity_threshold_unit`. |
| `sensitivity_threshold_unit` | When applicable | Unit for `sensitivity_threshold`. It is required when a threshold is entered and should be left blank otherwise. |
| `measurement_start` | Optional | Start date or period of the measurement, using `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` precision as supported by the source. |
| `measurement_end` | Optional | End date or period of the measurement, using the same formats. It must not precede `measurement_start`. |
| `comments` | Optional | Other concise context or caveats that do not fit the structured fields. Do not use it to replace provenance or source location. |
| `quality_flag` | Optional | Contributor's quality assessment: `high`, `moderate`, `low`, or `not_assessed` (the default). Explain non-default assessments in `quality_reason`. |
| `quality_reason` | Optional | Brief justification for the selected `quality_flag`, such as a known limitation or supporting cross-check. |
| `verified_against` | Optional | Indicates that a second contributor checked the value against the publication's text or table. Leave blank unless that review occurred. |

## Related workbook sheets

`NEW_EVENTS`, `NEW_PUBLICATIONS`, and `EVENT_ALIASES` are small registration sheets for entries missing from dropdown lists. `FIELDS` repeats the workbook field definitions, and `HOW TO` summarizes the workflow. The hidden `LISTS` sheet supplies dropdown options; it is generated from the project's registries.
