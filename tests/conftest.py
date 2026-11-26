"""
Pytest configuration and environment fixtures for CypherDNA test suite.
"""

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT_DIR, "core")

for p in [ROOT_DIR, CORE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)
