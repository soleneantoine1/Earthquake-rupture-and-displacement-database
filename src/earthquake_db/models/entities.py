from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from earthquake_db.models.enums import (
    Component,
    CoordinateOrigin,
    GeometryFormat,
    GeometryType,
    Method,
    MetricCategory,
    MetricDataType,
    QualityFlag,
    RelationshipType,
    ReviewStatus,
    SourceType,
    SpatialRepresentation,
    StatisticType,
    TargetType,
    UncertaintyType,
    ValueOrigin,
)


def enum_type(enum_class: type) -> SqlEnum:
    return SqlEnum(
        enum_class,
        name=f"{enum_class.__name__.lower()}_enum",
        native_enum=False,
        values_callable=lambda values: [member.value for member in values],
    )


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(
        enum_type(SourceType), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True)
    citation: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)

    datasets: Mapped[list[Dataset]] = relationship(back_populates="source")


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.source_id", ondelete="RESTRICT"), nullable=False
    )
    dataset_title: Mapped[str] = mapped_column(Text, nullable=False)
    source_location: Mapped[str | None] = mapped_column(Text)
    original_file_path: Mapped[str | None] = mapped_column(Text)
    value_origin: Mapped[ValueOrigin] = mapped_column(
        enum_type(ValueOrigin), nullable=False
    )
    default_method: Mapped[Method] = mapped_column(enum_type(Method), nullable=False)
    method_details: Mapped[str | None] = mapped_column(Text)
    measurement_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    measurement_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    spatial_resolution: Mapped[float | None] = mapped_column(Float)
    spatial_resolution_unit: Mapped[str | None] = mapped_column(String(32))
    sensitivity_threshold: Mapped[float | None] = mapped_column(Float)
    sensitivity_threshold_unit: Mapped[str | None] = mapped_column(String(32))
    comments: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str | None] = mapped_column(String(255))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus), nullable=False
    )

    source: Mapped[Source] = relationship(back_populates="datasets")
    observation_groups: Mapped[list[ObservationGroup]] = relationship(
        back_populates="dataset"
    )


class MetricDefinition(TimestampMixin, Base):
    __tablename__ = "metric_definitions"

    metric_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[MetricCategory] = mapped_column(
        enum_type(MetricCategory), nullable=False
    )
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    data_type: Mapped[MetricDataType] = mapped_column(
        enum_type(MetricDataType), nullable=False
    )
    canonical_unit: Mapped[str | None] = mapped_column(String(32))
    definition_version: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    observation_groups: Mapped[list[ObservationGroup]] = relationship(
        back_populates="metric"
    )


class Geometry(TimestampMixin, Base):
    __tablename__ = "geometries"
    __table_args__ = (
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_geometry_longitude_range",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_geometry_latitude_range",
        ),
        CheckConstraint(
            "geometry_type != 'point' OR "
            "(longitude IS NOT NULL AND latitude IS NOT NULL)",
            name="ck_point_geometry_coordinates",
        ),
    )

    geometry_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    geometry_type: Mapped[GeometryType] = mapped_column(
        enum_type(GeometryType), nullable=False
    )
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    geometry_text: Mapped[str | None] = mapped_column(Text)
    geometry_format: Mapped[GeometryFormat | None] = mapped_column(
        enum_type(GeometryFormat)
    )
    canonical_crs: Mapped[str] = mapped_column(
        String(32), default="EPSG:4326", nullable=False
    )
    original_crs: Mapped[str | None] = mapped_column(String(32))
    coordinate_origin: Mapped[CoordinateOrigin] = mapped_column(
        enum_type(CoordinateOrigin), nullable=False
    )
    coordinate_conversion_method: Mapped[str | None] = mapped_column(Text)
    source_spatial_data: Mapped[str | None] = mapped_column(Text)
    source_spatial_unit: Mapped[str | None] = mapped_column(String(32))
    source_reference_description: Mapped[str | None] = mapped_column(Text)
    horizontal_location_uncertainty_m: Mapped[float | None] = mapped_column(Float)
    geometry_version: Mapped[str | None] = mapped_column(String(32))

    target_references: Mapped[list[Target]] = relationship(
        back_populates="reference_geometry"
    )
    observations: Mapped[list[Observation]] = relationship(back_populates="geometry")


class Target(TimestampMixin, Base):
    __tablename__ = "targets"

    target_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    target_type: Mapped[TargetType] = mapped_column(
        enum_type(TargetType), nullable=False
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_target_id: Mapped[str | None] = mapped_column(
        ForeignKey("targets.target_id", ondelete="RESTRICT")
    )
    external_identifier: Mapped[str | None] = mapped_column(String(255))
    reference_geometry_id: Mapped[str | None] = mapped_column(
        ForeignKey("geometries.geometry_id", ondelete="RESTRICT")
    )
    comments: Mapped[str | None] = mapped_column(Text)

    parent_target: Mapped[Target | None] = relationship(
        remote_side=[target_id], back_populates="child_targets"
    )
    child_targets: Mapped[list[Target]] = relationship(back_populates="parent_target")
    reference_geometry: Mapped[Geometry | None] = relationship(
        back_populates="target_references"
    )
    observation_targets: Mapped[list[ObservationTarget]] = relationship(
        back_populates="target"
    )


class ObservationGroup(TimestampMixin, Base):
    __tablename__ = "observation_groups"

    observation_group_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.dataset_id", ondelete="RESTRICT"), nullable=False
    )
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_definitions.metric_id", ondelete="RESTRICT"), nullable=False
    )
    component: Mapped[Component | None] = mapped_column(enum_type(Component))
    source_unit: Mapped[str | None] = mapped_column(String(32))
    method_override: Mapped[Method | None] = mapped_column(enum_type(Method))
    spatial_representation: Mapped[SpatialRepresentation] = mapped_column(
        enum_type(SpatialRepresentation), nullable=False
    )
    comments: Mapped[str | None] = mapped_column(Text)

    dataset: Mapped[Dataset] = relationship(back_populates="observation_groups")
    metric: Mapped[MetricDefinition] = relationship(back_populates="observation_groups")
    observations: Mapped[list[Observation]] = relationship(
        back_populates="observation_group"
    )


class Observation(TimestampMixin, Base):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint(
            "(value_numeric IS NOT NULL AND value_text IS NULL) OR "
            "(value_numeric IS NULL AND value_text IS NOT NULL)",
            name="ck_observation_exactly_one_value",
        ),
        CheckConstraint(
            "uncertainty_lower IS NULL OR "
            "(value_numeric IS NOT NULL AND uncertainty_lower <= value_numeric)",
            name="ck_observation_uncertainty_lower",
        ),
        CheckConstraint(
            "uncertainty_upper IS NULL OR "
            "(value_numeric IS NOT NULL AND uncertainty_upper >= value_numeric)",
            name="ck_observation_uncertainty_upper",
        ),
        CheckConstraint(
            "(statistic_type = 'percentile' AND percentile_level IS NOT NULL AND "
            "percentile_level >= 0 AND percentile_level <= 100) OR "
            "(statistic_type != 'percentile' AND percentile_level IS NULL)",
            name="ck_observation_percentile_level",
        ),
        CheckConstraint(
            "sample_count IS NULL OR sample_count > 0",
            name="ck_observation_sample_count",
        ),
        CheckConstraint(
            "confidence_level IS NULL OR "
            "(confidence_level >= 0 AND confidence_level <= 100)",
            name="ck_observation_confidence_level",
        ),
        CheckConstraint(
            "depth_location_uncertainty_m IS NULL OR depth_location_uncertainty_m >= 0",
            name="ck_observation_depth_uncertainty",
        ),
    )

    record_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    observation_group_id: Mapped[str] = mapped_column(
        ForeignKey("observation_groups.observation_group_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_row_id: Mapped[str | None] = mapped_column(String(255))
    source_location: Mapped[str | None] = mapped_column(Text)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric)
    value_text: Mapped[str | None] = mapped_column(Text)
    statistic_type: Mapped[StatisticType] = mapped_column(
        enum_type(StatisticType), nullable=False
    )
    percentile_level: Mapped[float | None] = mapped_column(Float)
    sample_count: Mapped[int | None] = mapped_column(Integer)
    canonical_value: Mapped[Decimal | None] = mapped_column(Numeric)
    canonical_unit: Mapped[str | None] = mapped_column(String(32))
    uncertainty_lower: Mapped[Decimal | None] = mapped_column(Numeric)
    uncertainty_upper: Mapped[Decimal | None] = mapped_column(Numeric)
    uncertainty_type: Mapped[UncertaintyType] = mapped_column(
        enum_type(UncertaintyType), nullable=False
    )
    uncertainty_description: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[float | None] = mapped_column(Float)
    geometry_id: Mapped[str | None] = mapped_column(
        ForeignKey("geometries.geometry_id", ondelete="RESTRICT")
    )
    depth_m: Mapped[float | None] = mapped_column(Float)
    depth_location_uncertainty_m: Mapped[float | None] = mapped_column(Float)
    value_origin: Mapped[ValueOrigin | None] = mapped_column(enum_type(ValueOrigin))
    calculation: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    quality_flag: Mapped[QualityFlag] = mapped_column(
        enum_type(QualityFlag), nullable=False
    )
    quality_reason: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus), nullable=False
    )

    observation_group: Mapped[ObservationGroup] = relationship(
        back_populates="observations"
    )
    geometry: Mapped[Geometry | None] = relationship(back_populates="observations")
    targets: Mapped[list[ObservationTarget]] = relationship(
        back_populates="observation"
    )
    derived_inputs: Mapped[list[ObservationDerivation]] = relationship(
        foreign_keys="ObservationDerivation.derived_record_id",
        back_populates="derived_observation",
    )
    derivation_inputs: Mapped[list[ObservationDerivation]] = relationship(
        foreign_keys="ObservationDerivation.input_record_id",
        back_populates="input_observation",
    )


class ObservationTarget(Base):
    __tablename__ = "observation_targets"

    record_id: Mapped[str] = mapped_column(
        ForeignKey("observations.record_id", ondelete="RESTRICT"), primary_key=True
    )
    target_id: Mapped[str] = mapped_column(
        ForeignKey("targets.target_id", ondelete="RESTRICT"), primary_key=True
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        enum_type(RelationshipType), primary_key=True
    )

    observation: Mapped[Observation] = relationship(back_populates="targets")
    target: Mapped[Target] = relationship(back_populates="observation_targets")


class ObservationDerivation(Base):
    __tablename__ = "observation_derivations"
    __table_args__ = (
        CheckConstraint(
            "derived_record_id != input_record_id", name="ck_derivation_not_self"
        ),
        UniqueConstraint(
            "derived_record_id", "input_record_id", name="uq_derivation_input"
        ),
    )

    derived_record_id: Mapped[str] = mapped_column(
        ForeignKey("observations.record_id", ondelete="RESTRICT"), primary_key=True
    )
    input_record_id: Mapped[str] = mapped_column(
        ForeignKey("observations.record_id", ondelete="RESTRICT"), primary_key=True
    )
    input_role: Mapped[str | None] = mapped_column(Text)

    derived_observation: Mapped[Observation] = relationship(
        foreign_keys=[derived_record_id], back_populates="derived_inputs"
    )
    input_observation: Mapped[Observation] = relationship(
        foreign_keys=[input_record_id], back_populates="derivation_inputs"
    )
