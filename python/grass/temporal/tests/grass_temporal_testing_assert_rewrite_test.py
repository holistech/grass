"""Tests that a failed comparison in a helper of the testing package shows both values

pytest rewrites the assert statements of test modules and conftest.py only,
unless a package is registered. The helpers compare with a plain assert, and
without the rewrite the failure reads ``AssertionError`` and nothing else.
"""

import pytest

from grass.temporal.testing import algebra_cases


def test_a_failing_helper_assertion_shows_the_values(monkeypatch):
    def run(kind, expression, **options):
        return {"register": ["a", "b"]}

    monkeypatch.setattr(algebra_cases, "run_core", run)
    with pytest.raises(AssertionError) as excinfo:
        algebra_cases.check_dry("raster", "A", {}, {"register": 3})
    message = str(excinfo.value)
    assert "2 == 3" in message, message
