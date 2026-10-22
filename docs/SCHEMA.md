# Schema (generated from `scripts/schema.py` by `scripts/make_schema_doc.py` - that file is authoritative)

## `events`  (primary key: event_id)
The earthquake catalogue (one row per physical earthquake).

`event_id`, `event_name`, `event_date`, `mw`, `latitude`, `longitude`, `hypocenter_depth_km`, `centroid_depth_km`, `mechanism`, `region`, `coordinate_source`, `sequence_id`, `notes`

## `event_aliases`  (primary key: alias)
Other names/ids that resolve to an event.

`alias`, `alias_type`, `event_id`, `reason`

## `metrics`  (primary key: metric_id)
The metric catalogue (units, allowed statistics, plausible range).

`metric_id`, `display_name`, `category`, `value_type`, `canonical_unit`, `allowed_statistics`, `plausible_min`, `plausible_max`, `distribution_policy`, `definition_source`

## `sources`  (primary key: pub_id)
Atomic publications, databases, agencies, catalogues.

`pub_id`, `citation_short`, `citation_full`, `doi`, `kind`, `needs_full_reference`, `legacy_source_ids`, `note`

## `observations`  (primary key: obs_id)
One published value (or range / category) for one event, metric, study.

`obs_id`, `event_id`, `metric_id`, `pub_ids`, `compiled_in`, `statistic`, `value_num`, `qualifier`, `value_lo`, `value_hi`, `range_type`, `value_text`, `unit`, `component`, `segment`, `model_id`, `n`, `unc_type`, `unc_minus`, `unc_plus`, `unc_note`, `reported_text`, `source_location`, `method`, `method_details`, `origin`, `digitization_method`, `digitization_unc`, `dataset_id`, `group_id`, `source_row_id`, `spatial_representation`, `longitude`, `latitude`, `depth_m`, `horizontal_location_uncertainty_m`, `depth_location_uncertainty_m`, `coordinate_origin`, `coordinate_conversion_method`, `source_spatial_data`, `source_spatial_unit`, `source_reference_description`, `spatial_resolution`, `sensitivity_threshold`, `sensitivity_threshold_unit`, `measurement_start`, `measurement_end`, `quality_reason`, `confidence_level`, `review_status`, `quality`, `flags`, `comment`, `legacy_label`, `submitted_by`, `submitted_on`, `reviewed_by`, `reviewed_on`

## `arrays`  (primary key: array_id)
Header of an along-fault series published as a table/supplement.

`array_id`, `event_id`, `metric_id`, `pub_ids`, `compiled_in`, `component`, `segment`, `model_id`, `unit`, `source_location`, `method`, `method_details`, `derive_stats`, `unc_type`, `unc_note`, `n_values`, `origin`, `digitization_method`, `digitization_unc`, `dataset_id`, `group_id`, `spatial_representation`, `coordinate_origin`, `coordinate_conversion_method`, `source_spatial_unit`, `source_reference_description`, `spatial_resolution`, `sensitivity_threshold`, `sensitivity_threshold_unit`, `measurement_start`, `measurement_end`, `quality_reason`, `confidence_level`, `review_status`, `quality`, `flags`, `comment`, `legacy_array_id`, `submitted_by`, `submitted_on`, `reviewed_by`, `reviewed_on`

## `array_values`  (primary key: array_id, idx)
One measurement of an array (value, optional positive offsets, optional lat/lon).

`array_id`, `idx`, `value`, `unc_minus`, `unc_plus`, `lat`, `lon`, `source_position`

## Controlled vocabularies

- **STATISTICS**: `individual`, `minimum`, `mean`, `median`, `maximum`, `category`
- **UNC_TYPES**: `not_reported`, `1sigma`, `2sigma`, `ci95`, `minmax_range`, `unspecified`, `qualitative`, `credible_interval`
- **ORIGINS**: `reported`, `figure_digitized`
- **RANGE_TYPES**: `published_range`, `lower_bound`, `upper_bound`, `model_range`, `class_interval`
- **ALIAS_TYPES**: `legacy_id`, `name_variant`
- **REVIEW_STATUS**: `draft`, `reviewed_against_text`, `reviewed_against_table`, `verified`
- **QUALITY**: `low`, `moderate`, `high`, `not_assessed`
- **QUALIFIERS**: `(empty)`, `<`, `>`, `~`
- **FLAGS**: `needs_curation_unparsed_text`, `needs_curation_uncertainty`, `annotation_in_label`, `annotation_marker`, `original_pub_unresolved`, `value_from_range`, `segment_moved_from_component`
- **COMPONENTS**: `(empty)`, `strike-slip`, `vertical/throw (source code T)`, `fault-normal`, `net slip`, `opening`, `vertical/throw large aperture`, `strike-slip large aperture`, `geodetic displacement`, `field localized slip`, `fault-parallel`, `net slip large aperture`
- **KINDS**: `publication`, `database`, `agency`, `catalog`
- **MECHANISMS**: `Strike-slip`, `Reverse`, `Normal`, `Oblique`

## Keys
- Duplicate key (same study, same value twice -> error D001): `event_id, metric_id, pub_ids, statistic, component, segment, model_id, value_num, qualifier, value_lo, value_hi, value_text, longitude, latitude`
- Conflict key (one study, two different values -> error D002 unless distinguished): `event_id, metric_id, pub_ids, statistic, component, segment, model_id, longitude, latitude`

## Conventions
- Empty string = missing. Never `0`, `NA`, `-`.
- `unc_minus`/`unc_plus` are **positive offsets** from `value_num` (value - minus, value + plus). The build converts them to absolute bounds (`uncertainty_lower/upper` in `data.js`).
- `value_num` with `qualifier` (`<`,`>`,`~`) is a bound, not a measurement; `value_lo/value_hi` is a published range. Neither is ever plotted as a point.
- `pub_ids` is pipe-separated for joint attribution; `compiled_in` is a single `pub_id`.
- Arrays: `derive_stats=true` -> the build computes min/mean/median/max (never stored).
- OFD and SSD exist only as `off_fault_deformation_fraction` and `ssd_fraction` (unit `%`).

