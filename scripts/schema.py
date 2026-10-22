"""Canonical schema for the surface-rupture literature database.

Everything that defines what a valid row looks like lives here, so that the
migration, the validator and the build all agree.  Edit this file (and
docs/SCHEMA.md) when the data model changes -- never in the interfaces.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Directories can be redirected with environment variables (used by the tests and by
# the demo fixture), so that the same scripts run on live data or on a fixture.
DATA = Path(os.environ.get("RUPTURE_DATA_DIR", ROOT / "data"))
REPORTS = Path(os.environ.get("RUPTURE_REPORTS_DIR", ROOT / "reports"))
BASELINES = Path(os.environ.get("RUPTURE_BASELINES_DIR", ROOT / "baselines"))
SITE = Path(os.environ.get("RUPTURE_SITE_DIR", ROOT / "site"))
LEGACY = ROOT / "legacy"

# --------------------------------------------------------------------------
# Canonical tables (plain CSV, one row per fact, sorted by primary key)
# --------------------------------------------------------------------------
FILES = {
    "events": DATA / "events.csv",
    "event_aliases": DATA / "event_aliases.csv",
    "metrics": DATA / "metrics.csv",
    "sources": DATA / "sources.csv",
    "observations": DATA / "observations.csv",
    "arrays": DATA / "arrays.csv",
    "array_values": DATA / "array_values.csv",
}

# Optional context fields (all may be empty). Location block follows the contributor sheet.
LOC_FIELDS = [
    "spatial_representation", "longitude", "latitude", "depth_m", "horizontal_location_uncertainty_m",
    "depth_location_uncertainty_m", "coordinate_origin", "coordinate_conversion_method", "source_spatial_data",
    "source_spatial_unit", "source_reference_description",
]
CTX_FIELDS = [
    "spatial_resolution", "sensitivity_threshold", "sensitivity_threshold_unit", "measurement_start", "measurement_end",
    "quality_reason", "confidence_level",
]

COLUMNS = {
    "events": [
        "event_id", "event_name", "event_date", "mw", "latitude", "longitude",
        "hypocenter_depth_km", "centroid_depth_km", "mechanism", "region",
        "coordinate_source", "sequence_id", "notes",
    ],
    "event_aliases": ["alias", "alias_type", "event_id", "reason"],
    "metrics": [
        "metric_id", "display_name", "category", "value_type", "canonical_unit",
        "allowed_statistics", "plausible_min", "plausible_max",
        "distribution_policy", "definition_source",
    ],
    "sources": [
        "pub_id", "citation_short", "citation_full", "doi", "kind",
        "needs_full_reference", "legacy_source_ids", "note",
    ],
    "observations": [
        "obs_id", "event_id", "metric_id",
        "pub_ids",            # original measurement study/studies (| separated)
        "compiled_in",        # pub_id of the compilation it was read from, if any
        "statistic",
        "value_num", "qualifier", "value_lo", "value_hi", "range_type", "value_text", "unit",
        "component", "segment", "model_id", "n",
        "unc_type", "unc_minus", "unc_plus", "unc_note",
        "reported_text",      # the string exactly as published/ingested, when parsed
        "source_location", "method", "method_details",
        "origin", "digitization_method", "digitization_unc",
        "dataset_id", "group_id", "source_row_id",
        *LOC_FIELDS, *CTX_FIELDS,
        "review_status", "quality", "flags", "comment", "legacy_label",
        "submitted_by", "submitted_on", "reviewed_by", "reviewed_on",
    ],
    "arrays": [
        "array_id", "event_id", "metric_id", "pub_ids", "compiled_in",
        "component", "segment", "model_id", "unit", "source_location", "method",
        "method_details", "derive_stats", "unc_type", "unc_note", "n_values",
        "origin", "digitization_method", "digitization_unc",
        "dataset_id", "group_id", "spatial_representation", "coordinate_origin", "coordinate_conversion_method",
        "source_spatial_unit", "source_reference_description", *CTX_FIELDS,
        "review_status", "quality", "flags", "comment", "legacy_array_id",
        "submitted_by", "submitted_on", "reviewed_by", "reviewed_on",
    ],
    "array_values": ["array_id", "idx", "value", "unc_minus", "unc_plus", "lat", "lon", "source_position"],
}

PRIMARY_KEYS = {
    "events": ["event_id"],
    "event_aliases": ["alias"],
    "metrics": ["metric_id"],
    "sources": ["pub_id"],
    "observations": ["obs_id"],
    "arrays": ["array_id"],
    "array_values": ["array_id", "idx"],
}

# --------------------------------------------------------------------------
# Controlled vocabularies
# --------------------------------------------------------------------------
STATISTICS = ["individual", "minimum", "mean", "median", "maximum", "category"]

# unc_minus / unc_plus are ALWAYS positive offsets from the value (value - minus, value + plus).
# Never absolute bounds.  The build converts them to bounds for the plots.
UNC_TYPES = [
    "not_reported",   # the study gives no uncertainty
    "1sigma",         # one standard deviation
    "2sigma",         # two standard deviations
    "ci95",           # 95 % confidence interval
    "minmax_range",   # published min-max range around the value
    "unspecified",    # a +/- is published but the convention is not stated
    "qualitative",    # described in words only (put the words in unc_note)
    "credible_interval",  # Bayesian credible interval (give the level in confidence_level)
]

# origin: 'reported' = printed in text/table/supplement/data file.  'figure_digitized' = read off a
# figure (allowed only with method + reading uncertainty, kept SEPARATE from scientific uncertainty).
ORIGINS = ["reported", "figure_digitized"]
# A published interval without a central value (never an uncertainty, never turned into a midpoint)
RANGE_TYPES = ["published_range", "lower_bound", "upper_bound", "model_range", "class_interval"]
ALIAS_TYPES = ["legacy_id", "name_variant"]

REVIEW_STATUS = ["draft", "reviewed_against_text", "reviewed_against_table", "verified"]
QUALITY = ["low", "moderate", "high", "not_assessed"]
SPATIAL_REPRESENTATIONS = ["event_summary", "fault_summary", "point", "profile", "segment", "line", "polygon", "grid", "rupture_model"]
COORD_ORIGINS = ["source", "converted"]
QUALIFIERS = ["", "<", ">", "~"]

# Flags are pipe-separated tokens.  needs_* tokens appear in reports/curation_queue.csv.
FLAGS = [
    "needs_curation_unparsed_text",   # value could not be parsed into numbers
    "needs_curation_uncertainty",     # uncertainty present but its meaning is ambiguous
    "annotation_in_label",            # source label carried free-text notes (kept in legacy_label)
    "annotation_marker",              # value carried *, ** footnote markers
    "original_pub_unresolved",        # compilation does not name the underlying study
    "value_from_range",               # only a range was published
    "segment_moved_from_component",   # a fault/sub-event name was stored in component in v7
]

# Displacement / measurement components.  Add new ones deliberately.
COMPONENTS = [
    "", "strike-slip", "vertical/throw (source code T)", "fault-normal", "net slip",
    "opening", "vertical/throw large aperture", "strike-slip large aperture",
    "geodetic displacement", "field localized slip", "fault-parallel",
    "net slip large aperture",
]

KINDS = ["publication", "database", "agency", "catalog"]

# Suggested (not enforced) measurement methods -- free text is allowed, the list only feeds dropdowns.
METHODS = [
    "field", "geologic_mapping", "OIC", "InSAR", "GNSS", "seismic", "laboratory", "joint_inversion",
    "lidar_differencing", "finite_fault_model", "kinematic_slip_model", "geodetic_slip_model",
    "literature_compilation", "compiled_source", "other",
]
MECHANISMS = ["Strike-slip", "Reverse", "Normal", "Oblique"]
# Contributor-facing mapping of the 'verified_against' dropdown
VERIFIED_AGAINST = {"": "draft", "text": "reviewed_against_text", "table": "reviewed_against_table"}

# Ids: legacy v7 ids (R0000123, A0033) are kept; every NEW id is a hash of the scientific key
# (O + 12 hex), so two contributors adding different rows on different branches never collide
# and the same row entered twice collides on purpose.
ID_PATTERNS = {
    "obs_id": r"^(R\d{7}|O[0-9a-f]{12})$",
    "array_id": r"^(A\d{4,}|A[0-9a-f]{12})$",
    "pub_id": r"^[a-z0-9][a-z0-9\-_.]*$",
}

# Which statistics a numeric metric may carry
NUMERIC_STATS = ["individual", "minimum", "mean", "median", "maximum"]
CATEGORICAL_STATS = ["category"]

# Dedup key: the same study must not report the same value twice.
DUPLICATE_KEY = [
    "event_id", "metric_id", "pub_ids", "statistic", "component", "segment", "model_id",
    "value_num", "qualifier", "value_lo", "value_hi", "value_text", "longitude", "latitude",
]
# One study gives one summary statistic per (event, metric, component, model).
CONFLICT_KEY = ["event_id", "metric_id", "pub_ids", "statistic", "component", "segment", "model_id", "longitude", "latitude"]
