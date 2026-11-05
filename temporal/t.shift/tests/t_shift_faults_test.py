"""Test t.shift on a dataset whose maps another dataset registers as well"""

from grass.temporal.testing.data import create_timed_stds, day
from grass.temporal.testing.readback import list_maps


def _times(tools, name):
    return [(row.start, row.end) for row in list_maps(tools, "strds", name)]


def test_shift_of_extract_without_expression_moves_original(tools, prefix):
    """An extract without expression registers the maps of the original

    The time belongs to the map, so the shift of the extract moves the maps in
    the original dataset too; only an extract with an expression has maps of
    its own.
    """
    original = create_timed_stds(tools, prefix, [(day(0), day(1)), (day(1), day(2))])
    shared = f"{prefix}_shared"
    tools.t_rast_extract(input=original, output=shared)
    before = _times(tools, original)

    tools.t_shift(input=shared, granularity="10 days")

    assert _times(tools, shared) == _times(tools, original)
    assert _times(tools, original) != before
    assert _times(tools, original) == [
        ("2001-01-11 00:00:00", "2001-01-12 00:00:00"),
        ("2001-01-12 00:00:00", "2001-01-13 00:00:00"),
    ]


def test_shift_of_extract_with_expression_leaves_original(tools, prefix):
    original = create_timed_stds(tools, prefix, [(day(0), day(1)), (day(1), day(2))])
    own = f"{prefix}_own"
    tools.t_rast_extract(
        input=original, output=own, expression=original, basename=f"{prefix}_own"
    )
    before = _times(tools, original)

    tools.t_shift(input=own, granularity="10 days")

    assert _times(tools, original) == before
    assert _times(tools, own) != before
