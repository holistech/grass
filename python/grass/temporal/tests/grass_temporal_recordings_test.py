"""Compare the extent, granularity, date and topology functions with their record

The records in ``recordings/`` hold what the functions computed before the
library was refactored (see grass.temporal.testing.recordings for how they are
made). A failure names the case that changed. Never record again to make this
test pass: a deviation is either a bug in the change or a decision of the
maintainer.
"""

from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.testing import recordings

RECORDINGS = Path(__file__).parent / "recordings"


@pytest.fixture(scope="module", autouse=True)
def session(temporal_module_session):
    """Initialise grass.temporal the way the recording did"""
    tgis.init(raise_fatal_error=True)
    return temporal_module_session


@pytest.mark.parametrize("name", recordings.RECORD_NAMES)
def test_recording_matches(name):
    differences = recordings.differences(name, recordings.CASES[name](), RECORDINGS)
    assert not differences[:10], f"{len(differences)} cases differ"
    assert not differences


def test_recordings_are_complete():
    """Every record is there and no stray file is left in the directory"""
    found = sorted(path.name for path in RECORDINGS.iterdir())
    expected = [f"{name}.json.gz" for name in recordings.RECORD_NAMES]
    expected += [
        "database_read.json.gz",
        "database_structure.json",
        "database_write.sql",
    ]
    assert found == sorted(expected)
