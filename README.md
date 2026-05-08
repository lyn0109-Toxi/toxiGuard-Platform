# ToxiGuard-Platform

Integrated regulatory development strategy platform for ICH M7-aligned QSAR,
impurity/degradation evidence, ontology-guided submission planning, and
bioequivalence dissolution strategy support.

## Licensing and Use

This repository is proprietary unless a separate written agreement says
otherwise. See `LICENSE`.

Before using the platform for commercial, regulatory, or client-facing work,
review:

- `DISCLAIMER.md`: regulatory, scientific, FDA, USP/EP, and QSAR limitations
- `NOTICE.md`: open-source package and public data source notices
- `ASSET_ATTRIBUTION.md`: bundled image provenance and commercial-use tracking

This platform is not affiliated with, endorsed by, certified by, or approved by
FDA, ICH, USP, EP, NIH, NCI, PubChem, or any other regulatory or standards
organization.

## Streamlit Cloud Deployment

Use these settings when creating the app on Streamlit Community Cloud:

- Repository: `lyn0109-Toxi/ToxiGuard-Platform`
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
