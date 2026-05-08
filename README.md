# ToxiScope AI

Precision in silico toxicology and regulatory decision support platform for
ICH M7-aligned QSAR, impurity evidence, degradation profiling, and submission
narrative support.

## Streamlit Cloud Deployment

Use these settings when creating the app on Streamlit Community Cloud:

- Repository: `lyn0109-Toxi/ToxiScope`
- Branch: `main`
- Main file path: `streamlit_app.py`
- Python dependencies: `requirements.txt`

The cloud entry point imports `toxiscope_app.py`, so the local app and deployed
app use the same ToxiScope runtime.

## Local Run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Core Modules

- `core/regulatory.py`: compatibility API for app and tests
- `core/qsar.py`: expert and statistical structural alert logic
- `core/evidence.py`: evidence objects and source traceability
- `core/compendial.py`: USP/EP/DMF-style known impurity context
- `core/degradation.py`: predicted degradation product assessment
- `core/harness.py`: validation gates and worker-report style manifest
- `core/reporting.py`: regulatory narrative generation
