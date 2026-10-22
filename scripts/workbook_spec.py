"""Single definition of the contributor workbook (used by make_template.py and ingest.py).

The main sheet INGESTION has one row per published value. Its columns are the contributor-facing field
names, grouped as Identification / Value / Uncertainty / Location / Method.  ingest.py maps them onto the
canonical tables (docs/SCHEMA.md); nothing here is stored as-is.

Each field: (name, required, width, dropdown list name or None, description)
required: "yes" | "when" (conditionally, see description) | "" (optional)
"""

IDENT = "Identification and provenance"
VALUE = "Value"
UNC = "Uncertainty"
LOC = "Location"
METH = "Method and comments"

FIELDS = [
    (IDENT, [
        ("dataset_id", "", 16, None, "Optional. Name of the dataset the value comes from (e.g. a supplement file or a data repository id)."),
        ("observation_group_id", "", 18, None, "Optional label of your choice. Rows sharing it are related values of one dataset. If two or more rows share it and all have statistic_type 'individual', they are stored as ONE series (array): the database then computes minimum/mean/median/maximum itself."),
        ("source_row_id", "", 12, None, "Optional. Row number or identifier in the original table (helps reviewers)."),
        ("metric_id", "yes", 30, "metrics", "Controlled metric name, e.g. surface_fault_slip. Pick from the list."),
        ("target_id", "yes", 36, "events", "The earthquake (event). Pick from the list; if it is missing add it in NEW_EVENTS (other names for an existing event: EVENT_ALIASES)."),
        ("source_id", "yes", 32, "pubs", "The ORIGINAL study the value comes from. Pick from the list; if missing add it in NEW_PUBLICATIONS (full reference + DOI)."),
        ("compiled_in", "", 28, "pubs", "Only if you read the value in a compilation (e.g. a database or review paper): put the original study in source_id and the compilation here."),
        ("source_location", "yes", 28, None, "Page, table, figure caption, supplement file or dataset field, e.g. 'Table 2, row 3'."),
        ("value_origin", "", 12, "origins", "reported (default) or digitized. 'digitized' = read off a figure: needs digitization_method and digitization_unc. database_derived is NOT allowed here: the database computes those itself."),
        ("digitization_method", "when", 24, None, "Only for digitized values: software, axis calibration, panel."),
        ("digitization_unc", "when", 12, None, "Only for digitized values: positive reading uncertainty, in the unit of the value. Separate from the paper's own uncertainty."),
    ]),
    (VALUE, [
        ("value", "when", 12, None, "The number exactly as published, in the canonical unit of the metric. For a categorical metric (mechanism, lithology, supershear class) write the category here. Leave empty if the paper gives only a range. Never write 0 for 'missing'."),
        ("value_range_low", "", 11, None, "Only if the paper gives a range instead of a number (e.g. '113-140 km'): lower end."),
        ("value_range_high", "", 11, None, "Upper end of the published range. Never a midpoint, never an uncertainty."),
        ("qualifier", "", 10, "qualifiers", "< or > or ~ if the paper gives an inequality or approximation ('<14 m': value=14, qualifier='<')."),
        ("unit", "when", 10, None, "Leave empty to use the canonical unit. A different unit is rejected: convert it and keep the printed form in reported_text."),
        ("statistic_type", "yes", 14, "statistics", "What the study reports: individual, minimum, mean, median, maximum. Categorical metrics: category (or leave empty)."),
        ("sample_count", "", 10, None, "Number of measurements represented by a summary statistic."),
        ("component", "when", 24, "components", "Displacement component, if the study reports one (strike-slip, vertical/throw, net slip...)."),
        ("segment", "", 22, None, "Fault segment / strand / sub-event the value applies to."),
        ("model_id", "", 20, None, "Slip model / dataset / solution name. Needed to tell apart several values from one study (e.g. SSD from different slip models)."),
        ("reported_text", "", 22, None, "The value as printed, if you had to convert it (e.g. '3.2 +0.5/-0.3 m', '320 cm')."),
        ("derive_stats", "", 11, "yesno", "Series only: yes (default) = database computes min/mean/median/max from the series; no = store the series only."),
    ]),
    (UNC, [
        ("uncertainty_type", "when", 16, "unc_types", "How the paper defines its uncertainty: 1_sigma, 2_sigma, 95_ci, credible_interval, range, qualitative, unspecified (a +/- with no stated convention), not_reported. Leave empty if none is reported."),
        ("uncertainty_minus", "when", 12, None, "POSITIVE offset below the value (value - uncertainty_minus). Never an absolute bound, never signed. Symmetric +/-x: put x in both columns."),
        ("uncertainty_plus", "when", 12, None, "POSITIVE offset above the value (value + uncertainty_plus)."),
        ("uncertainty_description", "when", 26, None, "Free text: required for 'qualitative'; use it for any unusual definition."),
        ("confidence_level", "", 10, None, "Number in (0,100], e.g. 95, when the interval has a stated confidence/credible level."),
    ]),
    (LOC, [
        ("spatial_representation", "", 16, "spatial", "event_summary (default), fault_summary, point, profile, segment, line, polygon, grid or rupture_model."),
        ("longitude", "when", 11, None, "Decimal degrees WGS84 of the measurement/summary. For a series: one per row if the table gives positions."),
        ("latitude", "when", 11, None, "Decimal degrees WGS84."),
        ("depth_m", "", 10, None, "Representative depth in metres."),
        ("horizontal_location_uncertainty_m", "", 12, None, "Positional uncertainty in metres."),
        ("depth_location_uncertainty_m", "", 12, None, "Depth uncertainty in metres."),
        ("coordinate_origin", "when", 12, "coord_origin", "Required if longitude/latitude are given: 'source' (published as coordinates) or 'converted' (you converted them, e.g. from along-strike distance)."),
        ("coordinate_conversion_method", "when", 22, None, "Required if converted: how you converted the published position to longitude/latitude."),
        ("source_spatial_data", "", 14, None, "Original published position, e.g. 35 (km along strike). For a series: one per row."),
        ("source_spatial_unit", "when", 12, None, "Unit of source_spatial_data (required with it and if converted)."),
        ("source_reference_description", "when", 26, None, "Published origin and reference system of the position (e.g. 'km from the southern end of the rupture')."),
    ]),
    (METH, [
        ("method", "yes", 22, "methods", "Broad method: field, OIC, InSAR, GNSS, seismic, geologic_mapping, laboratory, joint_inversion, ... (list suggests; free text allowed)."),
        ("method_details", "", 30, None, "Short description of processing or measurement choices."),
        ("spatial_resolution", "", 16, None, "Smallest spatial scale resolved by the measurement, with unit (e.g. '30 m')."),
        ("sensitivity_threshold", "", 12, None, "Minimum sensitivity threshold of the method (number)."),
        ("sensitivity_threshold_unit", "when", 12, None, "Unit of the sensitivity threshold."),
        ("measurement_start", "", 12, None, "Start date of the measurement: YYYY, YYYY-MM or YYYY-MM-DD."),
        ("measurement_end", "", 12, None, "End date of the measurement (same formats)."),
        ("comments", "", 30, None, "Important distinctions a reviewer should know."),
        ("quality_flag", "", 12, "quality", "high, moderate, low or not_assessed (default)."),
        ("quality_reason", "", 26, None, "Concise justification for the quality flag."),
        ("verified_against", "", 12, "verified", "text or table, only if a second person checked the value against the paper."),
    ]),
]

INGESTION_COLUMNS = [f[0] for _, fs in FIELDS for f in fs]

# small side sheets (only used when something is missing from the dropdown lists)
SIDE_SHEETS = {
    "NEW_EVENTS": [
        ("event_name", "yes", 28, None, "Common name, e.g. 'Ridgecrest 2'."),
        ("event_date", "yes", 12, None, "UTC date YYYY-MM-DD."),
        ("mw", "yes", 8, None, "Preferred Mw (other published values go in INGESTION as moment_magnitude)."),
        ("latitude", "yes", 11, None, "Epicentre, decimal degrees."),
        ("longitude", "yes", 11, None, ""),
        ("hypocenter_depth_km", "", 12, None, ""),
        ("centroid_depth_km", "", 12, None, ""),
        ("mechanism", "yes", 14, "mechanisms", ""),
        ("region", "", 18, None, "Country or region."),
        ("coordinate_source", "yes", 26, None, "Where the coordinates come from (catalogue / paper)."),
        ("sequence_id", "", 18, None, "Shared id for foreshock/mainshock/aftershock sequences."),
        ("notes", "", 30, None, ""),
        ("aliases", "", 28, None, "Other names for this event, separated by |."),
        ("confirm_distinct", "", 12, "yesno", "yes = I checked this is NOT an existing event under another name/magnitude."),
    ],
    "NEW_PUBLICATIONS": [
        ("citation_short", "yes", 30, None, "'Surname et al. (year)', 'A and B (year)' or 'Surname (year)'. Add a/b for same-author-same-year papers."),
        ("citation_full", "yes", 60, None, "Full reference."),
        ("doi", "when", 28, None, "10.xxxx/... (no URL)."),
        ("no_doi_reason", "when", 24, None, "Required if there is no DOI (book, report, historical paper)."),
        ("kind", "", 12, "kinds", "publication (default), database, agency, catalog."),
        ("note", "", 30, None, ""),
    ],
    "EVENT_ALIASES": [
        ("alias", "yes", 28, None, "Another name or spelling of an EXISTING event."),
        ("event", "yes", 36, "events", "Pick the canonical event."),
        ("reason", "", 36, None, "Why (e.g. 'Mw 7.3 vs 7.6 in other studies: same earthquake')."),
    ],
}
SIDE_COLUMNS = {k: [f[0] for f in v] for k, v in SIDE_SHEETS.items()}

EXAMPLE_MARK = "[EXAMPLE]"
