from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from earthquake_db.database import (
    database_session,
    initialize_database,
    seeded_metric_ids,
    table_names,
)
from earthquake_db.models import (
    CoordinateOrigin,
    Dataset,
    Geometry,
    GeometryType,
    Method,
    MetricDefinition,
    Observation,
    ObservationDerivation,
    ObservationGroup,
    ObservationTarget,
    QualityFlag,
    RelationshipType,
    ReviewStatus,
    Source,
    SourceType,
    SpatialRepresentation,
    StatisticType,
    Target,
    TargetType,
    UncertaintyType,
    ValueOrigin,
)


@pytest.fixture
def engine(tmp_path: Path):
    return initialize_database(tmp_path / "ridgecrest.sqlite")


def add_source_dataset_group(
    session: Session,
    metric_id: str = "moment_magnitude",
    group_id: str = "group-1",
) -> ObservationGroup:
    source = Source(
        source_id="source-1",
        source_type=SourceType.PUBLICATION,
        title="Pilot source",
    )
    dataset = Dataset(
        dataset_id="dataset-1",
        source=source,
        dataset_title="Pilot dataset",
        value_origin=ValueOrigin.REPORTED,
        default_method=Method.SEISMIC,
        review_status=ReviewStatus.DRAFT,
    )
    group = ObservationGroup(
        observation_group_id=group_id,
        dataset=dataset,
        metric_id=metric_id,
        spatial_representation=SpatialRepresentation.POINT,
    )
    session.add(group)
    return group


def add_observation(
    session: Session,
    group: ObservationGroup,
    record_id: str = "record-1",
    **values: object,
) -> Observation:
    defaults = {
        "record_id": record_id,
        "observation_group": group,
        "statistic_type": StatisticType.INDIVIDUAL,
        "uncertainty_type": UncertaintyType.NONE,
        "quality_flag": QualityFlag.NOT_ASSESSED,
        "review_status": ReviewStatus.DRAFT,
    }
    defaults.update(values)
    observation = Observation(**defaults)
    session.add(observation)
    return observation


def test_all_tables_can_be_created(engine) -> None:
    assert table_names(engine) == [
        "datasets",
        "geometries",
        "metric_definitions",
        "observation_derivations",
        "observation_groups",
        "observation_targets",
        "observations",
        "sources",
        "targets",
    ]


def test_sqlite_foreign_keys_are_enabled(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_metric_seed_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "seeded.sqlite"
    first_engine = initialize_database(path)
    second_engine = initialize_database(path)

    assert seeded_metric_ids(first_engine) == seeded_metric_ids(second_engine)
    with database_session(second_engine) as session:
        assert (
            session.scalar(
                select(MetricDefinition.metric_id)
                .order_by(MetricDefinition.metric_id)
                .limit(1)
            )
            == "earthquake_mechanism"
        )
        assert session.query(MetricDefinition).count() == 7


def test_valid_normalized_chain_and_event_target(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        observation = add_observation(session, group, value_numeric=7.1)
        target = Target(
            target_id="event-ridgecrest-mainshock",
            target_type=TargetType.EVENT,
            display_name="2019 Mw 7.1 Ridgecrest mainshock",
        )
        session.add(target)
        session.flush()
        session.add(
            ObservationTarget(
                record_id=observation.record_id,
                target_id=target.target_id,
                relationship_type=RelationshipType.ASSOCIATED,
            )
        )
        session.commit()

        assert session.get(Observation, "record-1") is not None
        assert session.get(Target, "event-ridgecrest-mainshock") is not None


def test_categorical_and_numerical_values_are_type_checked(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(session, group, value_numeric=7.1)
        session.commit()

        categorical_group = ObservationGroup(
            observation_group_id="mechanism-group",
            dataset_id="dataset-1",
            metric_id="earthquake_mechanism",
            spatial_representation=SpatialRepresentation.POINT,
        )
        session.add(categorical_group)
        add_observation(
            session,
            categorical_group,
            record_id="mechanism-record",
            value_text="strike_slip",
        )
        session.commit()

        invalid_group = ObservationGroup(
            observation_group_id="invalid-group",
            dataset_id="dataset-1",
            metric_id="earthquake_mechanism",
            spatial_representation=SpatialRepresentation.POINT,
        )
        session.add(invalid_group)
        add_observation(
            session, invalid_group, record_id="invalid-record", value_numeric=1.0
        )
        with pytest.raises(ValueError, match="categorical"):
            session.commit()
        session.rollback()

    with database_session(engine) as session:
        group = add_source_dataset_group(session, group_id="numeric-text-group")
        add_observation(session, group, value_text="7.1")
        with pytest.raises(ValueError, match="numerical"):
            session.commit()


def test_observation_requires_exactly_one_value(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(session, group, value_numeric=7.1, value_text="7.1")
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with database_session(engine) as session:
        group = add_source_dataset_group(session, group_id="empty-group")
        add_observation(session, group, record_id="empty-record")
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_invalid_point_coordinates_are_rejected(engine) -> None:
    with database_session(engine) as session:
        session.add(
            Geometry(
                geometry_id="bad-point",
                geometry_type=GeometryType.POINT,
                longitude=181,
                latitude=35,
                coordinate_origin=CoordinateOrigin.SOURCE,
            )
        )
        with pytest.raises(ValueError, match="longitude"):
            session.commit()


def test_invalid_uncertainty_bounds_are_rejected(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(
            session,
            group,
            value_numeric=7.1,
            uncertainty_lower=7.2,
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_percentile_requires_valid_level(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(
            session,
            group,
            value_numeric=7.1,
            statistic_type=StatisticType.PERCENTILE,
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.parametrize("percentile_level", [-1, 101])
def test_invalid_percentile_levels_are_rejected(engine, percentile_level: int) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(
            session,
            group,
            value_numeric=7.1,
            statistic_type=StatisticType.PERCENTILE,
            percentile_level=percentile_level,
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.parametrize("percentile_level", [0, 100, 50])
def test_valid_percentile_levels_are_accepted(engine, percentile_level: int) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(
            session,
            group,
            value_numeric=7.1,
            statistic_type=StatisticType.PERCENTILE,
            percentile_level=percentile_level,
        )
        session.commit()


def test_percentile_level_is_rejected_for_non_percentile(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(session, group, value_numeric=7.1, percentile_level=50)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_duplicate_observation_targets_are_rejected(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        observation = add_observation(session, group, value_numeric=7.1)
        target = Target(
            target_id="target-1",
            target_type=TargetType.EVENT,
            display_name="Event",
        )
        session.add_all([observation, target])
        session.flush()
        relationship = ObservationTarget(
            record_id=observation.record_id,
            target_id=target.target_id,
            relationship_type=RelationshipType.ASSOCIATED,
        )
        session.add(relationship)
        session.commit()
        with pytest.raises(IntegrityError):
            session.execute(
                insert(ObservationTarget).values(
                    record_id=observation.record_id,
                    target_id=target.target_id,
                    relationship_type=RelationshipType.ASSOCIATED,
                )
            )
        session.rollback()


def test_self_referential_derivation_is_rejected(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        add_observation(session, group, value_numeric=7.1)
        session.flush()
        session.add(
            ObservationDerivation(
                derived_record_id="record-1",
                input_record_id="record-1",
            )
        )
        with pytest.raises(ValueError, match="itself"):
            session.commit()


def test_referenced_parent_cannot_be_deleted(engine) -> None:
    with database_session(engine) as session:
        group = add_source_dataset_group(session)
        source = group.dataset.source
        session.commit()
        session.delete(source)
        with pytest.raises((IntegrityError, ValueError)):
            session.commit()
