"""Test configuration.

``scripts/`` holds build tooling rather than importable package code, so it is
not on the path by default. The docs generator has enough logic to be worth
testing, so make it importable here.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
