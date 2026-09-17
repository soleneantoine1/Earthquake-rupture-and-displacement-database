from enum import StrEnum


class SourceType(StrEnum):
    PUBLICATION = "publication"
    REPOSITORY = "repository"
    CATALOG = "catalog"
    OTHER = "other"


class MetricCategory(StrEnum):
    EVENT_SUMMARY = "event_summary"
    FAULT_SUMMARY = "fault_summary"


class MetricDataType(StrEnum):
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"


class TargetType(StrEnum):
    EVENT = "event"
    FAULT = "fault"
    FAULT_SECTION = "fault_section"


class ValueOrigin(StrEnum):
    REPORTED = "reported"
    DIGITIZED = "digitized"
    DATABASE_DERIVED = "database_derived"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class StatisticType(StrEnum):
    INDIVIDUAL = "individual"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    MEAN = "mean"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    CATEGORY = "category"


class Component(StrEnum):
    STRIKE_SLIP = "strike_slip"
    DIP_SLIP = "dip_slip"
    TOTAL = "total"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    ALONG_STRIKE = "along_strike"
    ALONG_DIP = "along_dip"
    OTHER = "other"


class UncertaintyType(StrEnum):
    NONE = "none"
    STANDARD_DEVIATION = "standard_deviation"
    STANDARD_ERROR = "standard_error"
    CONFIDENCE_INTERVAL = "confidence_interval"
    RANGE = "range"
    OTHER = "other"


class SpatialRepresentation(StrEnum):
    POINT = "point"
    PROFILE = "profile"
    SEGMENT = "segment"
    LINE = "line"
    POLYGON = "polygon"
    GRID = "grid"
    RUPTURE_MODEL = "rupture_model"


class GeometryType(StrEnum):
    POINT = "point"
    LINE = "line"
    POLYGON = "polygon"
    PROFILE = "profile"
    SEGMENT = "segment"
    GRID = "grid"
    RUPTURE_MODEL = "rupture_model"


class GeometryFormat(StrEnum):
    WKT = "wkt"
    GEOJSON = "geojson"


class CoordinateOrigin(StrEnum):
    SOURCE = "source"
    CONVERTED = "converted"


class Method(StrEnum):
    FIELD = "field"
    OIC = "oic"
    INSAR = "insar"
    GNSS = "gnss"
    SEISMIC = "seismic"
    GEOLOGIC_MAPPING = "geologic_mapping"
    LABORATORY = "laboratory"
    JOINT_INVERSION = "joint_inversion"
    OTHER = "other"


class QualityFlag(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    NOT_ASSESSED = "not_assessed"


class RelationshipType(StrEnum):
    ASSOCIATED = "associated"
    LOCATED_AT = "located_at"
    MEASURED_ON = "measured_on"
    PARENT = "parent"
    OTHER = "other"
