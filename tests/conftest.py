"""
Plumbing only, so `python -m pytest tests/` can import the project modules.

These pytest tests live in `tests/` deliberately. The three suites at the
project root (`test_units.py`, `test_regression.py`, `test_etymology_db.py`)
RUN ON IMPORT -- they are scripts using a `check(label, condition)` helper,
not collectable test functions -- so letting pytest discover them would
execute the whole legacy suite as a collection side effect.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
