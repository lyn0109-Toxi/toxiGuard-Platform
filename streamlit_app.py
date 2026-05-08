"""Streamlit Cloud entry point for ToxiScope AI.

Streamlit Community Cloud executes `streamlit_app.py` by default. The actual
application remains in `toxiscope_app.py` so local development and cloud
deployment share the same runtime path.
"""

from pathlib import Path
import sys


APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import toxiscope_app  # noqa: F401,E402
