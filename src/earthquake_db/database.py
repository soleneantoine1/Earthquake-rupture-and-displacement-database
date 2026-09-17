from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from earthquake_db.models.entities import (
    Base,
    Geometry,
    MetricDefinition,
    Observation,
    ObservationDerivation,
    ObservationGroup,
)
from earthquake_db.seed import load_metric_definitions
from earthquake_db.validation.rules import validate_geometry, validate_observation_value


def create_sqlite_engine(path: str | Path) -> Engine:
    database_url = (
        "sqlite:///:memory:" if str(path) == ":memory:" else f"sqlite:///{Path(path)}"
    )
    if str(path) != ":memory:":
        database_path = Path(path)
        if database_path.exists() and database_path.is_dir():
            raise ValueError(f"database path is a directory: {database_path}")
        database_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, future=True)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(
        dbapi_connection: Any, _connection_record: Any
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def initialize_database(
    path: str | Path, metric_definitions_path: str | Path | None = None
) -> Engine:
    engine = create_sqlite_engine(path)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(engine, expire_on_commit=False)
    with session_factory.begin() as session:
        if metric_definitions_path is None:
            load_metric_definitions(session)
        else:
            load_metric_definitions(session, metric_definitions_path)
    return engine


def database_session(engine: Engine) -> Session:
    return sessionmaker(engine, expire_on_commit=False)()


@event.listens_for(Session, "before_flush")
def _validate_scientific_records(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    for instance in session.new.union(session.dirty):
        if isinstance(instance, Geometry):
            validate_geometry(instance)
        elif isinstance(instance, Observation):
            group = instance.observation_group
            if group is None:
                group = session.get(ObservationGroup, instance.observation_group_id)
            if group is not None:
                metric = group.metric or session.get(MetricDefinition, group.metric_id)
                if metric is not None:
                    validate_observation_value(instance, metric)
        elif isinstance(instance, ObservationDerivation):
            if instance.derived_record_id == instance.input_record_id:
                raise ValueError("an observation cannot derive from itself")


def table_names(engine: Engine) -> list[str]:
    return sorted(inspect(engine).get_table_names())


def seeded_metric_ids(engine: Engine) -> list[str]:
    with database_session(engine) as session:
        from earthquake_db.models.entities import MetricDefinition

        return list(
            session.scalars(
                select(MetricDefinition.metric_id).order_by(MetricDefinition.metric_id)
            )
        )
