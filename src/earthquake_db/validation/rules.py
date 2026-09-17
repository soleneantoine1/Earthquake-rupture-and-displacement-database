from __future__ import annotations

from earthquake_db.models.entities import Geometry, MetricDefinition, Observation
from earthquake_db.models.enums import MetricDataType


def validate_geometry(geometry: Geometry) -> None:
    if geometry.longitude is not None and not -180 <= geometry.longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    if geometry.latitude is not None and not -90 <= geometry.latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if geometry.geometry_type.value == "point":
        if geometry.longitude is None or geometry.latitude is None:
            raise ValueError("point geometries require longitude and latitude")


def validate_observation_value(
    observation: Observation, metric: MetricDefinition
) -> None:
    has_numeric = observation.value_numeric is not None
    has_text = observation.value_text is not None
    if metric.data_type == MetricDataType.NUMERICAL and has_text and not has_numeric:
        raise ValueError("numerical metrics require value_numeric")
    if metric.data_type == MetricDataType.CATEGORICAL and has_numeric and not has_text:
        raise ValueError("categorical metrics require value_text")
    if metric.data_type == MetricDataType.NUMERICAL and metric.canonical_unit:
        if observation.canonical_unit != metric.canonical_unit:
            raise ValueError(
                "numerical observations require the metric canonical unit "
                f"({metric.canonical_unit})"
            )
