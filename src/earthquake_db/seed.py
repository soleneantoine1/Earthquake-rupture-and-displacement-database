from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from earthquake_db.models.entities import MetricDefinition
from earthquake_db.models.enums import MetricCategory, MetricDataType

DEFAULT_METRIC_DEFINITIONS = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "metric_definitions.json"
)


class MetricDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    display_name: str
    category: MetricCategory
    definition: str
    data_type: MetricDataType
    canonical_unit: str | None = None
    definition_version: str
    active: bool = True


def load_metric_definitions(
    session: Session, path: str | Path = DEFAULT_METRIC_DEFINITIONS
) -> list[str]:
    with Path(path).open(encoding="utf-8") as seed_file:
        seeds = [
            MetricDefinitionSeed.model_validate(item) for item in json.load(seed_file)
        ]

    loaded_ids: list[str] = []
    for seed in seeds:
        existing = session.get(MetricDefinition, seed.metric_id)
        if existing is None:
            session.add(MetricDefinition(**seed.model_dump()))
        loaded_ids.append(seed.metric_id)
    session.flush()
    return loaded_ids
