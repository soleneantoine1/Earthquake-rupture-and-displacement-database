# Ridgecrest Earthquake Database

This project is the foundation for a focused pilot database for the 2019
Ridgecrest earthquake sequence. The Mw 7.1 mainshock is the primary event, and
the Mw 6.4 foreshock is represented separately.

## Scope

The first pilot will eventually organize data from Milliner et al. surface-
deformation data, USGS event and rupture/GIS information, and one finite-fault
model. Data will not be downloaded or ingested until the foundation is
reviewed. A web interface and PostgreSQL/PostGIS deployment are out of scope
for this stage.

The planned lean architecture is:

```text
source -> dataset -> observation_group -> observation
```

The model is intended to accommodate metric definitions, observation targets,
events, faults, fault sections, geometries, values, units, uncertainties,
methods, quality information, and provenance. The initial implementation will
add these concepts incrementally rather than attempting a complete
earthquake-science schema at once. Geometry storage will remain database-
agnostic so PostGIS can be added later.

## Development status

This branch contains only the Python package foundation and test/tooling
configuration. Scientific schemas and ingestion adapters are not implemented.

## Development commands

Create the repository-local Conda environment with Python 3.12:

```bash
conda create --prefix ./.venv python=3.12 pip -y
conda activate ./.venv
python --version  # Python 3.12.14
python -m pip --version  # pip 26.2.1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

