"""Compare what the library writes to and reads from the temporal database

database_write.sql is the temporal database after a scenario that runs every
kind of write the library has (see grass.temporal.testing.database_image), with
times, user and register table names replaced by fixed values.
database_read.json.gz holds what the library prints and returns when it reads
that database back. Both were taken before the library was refactored. A
failure here means a change altered the stored rows or what a read makes of
them. Never record again to make this test pass.
"""

import difflib
import re
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.testing import database_image, recordings
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

RECORDINGS = Path(__file__).parent / "recordings"


def test_write_image_matches(tmp_path):
    expected = (RECORDINGS / "database_write.sql").read_text(encoding="utf-8")
    with temporal_session(tmp_path / "project") as session:
        database_image.write_scenario(
            Tools(session=session, consistent_return_value=True)
        )
        actual = database_image.normalized_dump(Path(tgis.get_tgis_database_string()))
    if actual != expected:
        lines = difflib.unified_diff(
            expected.splitlines(), actual.splitlines(), "recorded", "actual", n=0
        )
        shown = [line[:300] for line in lines][:20]
        pytest.fail("The database image differs:\n" + "\n".join(shown))


def test_read_image_matches(tmp_path):
    image = (RECORDINGS / "database_write.sql").read_text(encoding="utf-8")
    with temporal_session(tmp_path / "project"):
        database_image.load_image(image, Path(tgis.get_tgis_database_string()))
        differences = recordings.compare(
            "database_read", database_image.read_cases(), RECORDINGS
        )
    assert not differences[:10], f"{len(differences)} cases differ"


def test_image_has_no_volatile_values():
    """The recorded image holds no temporary path and no creation time of the run"""
    image = (RECORDINGS / "database_write.sql").read_text(encoding="utf-8")
    assert "/tmp/" not in image
    assert not re.search(r"'\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+'", image)
