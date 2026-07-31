# BRIF.AI

BRIF.AI architectural decision support platform bootstrap.

This repository currently contains only the Python project and quality infrastructure. Architectural domain models, validators, rule engines, and rulepack content are intentionally out of scope for this bootstrap.

## Requirements

- Python 3.12

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Developer Commands

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
python -m pytest
```

## Streamlit Demo

```powershell
py -3.13 -m pip install -e ".[dev,demo]"
py -3.13 -m streamlit run apps/daily_routines_demo.py
```

## Pre-commit

```powershell
python -m pre_commit install
python -m pre_commit run --all-files
```

