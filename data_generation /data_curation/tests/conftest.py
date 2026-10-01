import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


@pytest.fixture(scope="session")
def built():
    """One full deterministic build shared by every pipeline test (no files written)."""
    import build_dataset as BD
    out, st = BD.build_all()
    return out, st
