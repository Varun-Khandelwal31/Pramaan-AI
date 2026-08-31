"""
PRAMAAN Medico-Legal Evidence Platform
Top-level application entrypoint
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app

__all__ = ["app"]
