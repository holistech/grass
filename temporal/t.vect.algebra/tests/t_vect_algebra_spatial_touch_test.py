"""A selection with r or u under -s and maps whose boxes only touch

Under -s two maps are related when they are related in time and in space.
Touching at an edge or a corner is no spatial relation. The classic profile and
the core follow this; the reference implementation (grass.temporal.classic)
picks the maps to keep with the spatial test but takes the time to stamp from
the temporal relations alone, so a partner that only touches changes the
result. Decision of 23.10.2026: the profile stays as it is and the difference
is documented as a correction of the classic algebra.

The maps of the datasets are single squares. A result is compared by the times
of its maps only, sorted, because the squares are alike. Boxes
(x range, y range 0..10 unless noted) and times (2001-01-DD, ends exclusive
in the sense of the relation, not of the day):

=====  =====================  ===========
map    box                    time
=====  =====================  ===========
a1     0..10                  01.-02.01.
a2     100..110               01.-02.01.
a3     0..10                  05.-06.01.
a4     10..20, y 10..20       01.-02.01.
b1     0..10                  02.-03.01.
b2     200..210               02.-04.01.
b3     10..20, y 10..20       02.-05.01.
=====  =====================  ===========

A holds a1 to a4, B holds b1 and b2, C holds b1 to b3. The corner (10, 10)
is shared by a1 and b1 with a4, and by a1 with b3.
"""

from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, day, register_stds
from grass.temporal.testing.differential import RUNNERS, outcome
from grass.tools import Tools

KIND = "vector"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

# name: (unused, west, east, south, north, first day, last day)
MAPS = {
    "a1": (1, 0, 10, 0, 10, 1, 2),
    "a2": (2, 100, 110, 0, 10, 1, 2),
    "a3": (3, 0, 10, 0, 10, 5, 6),
    "a4": (4, 10, 20, 10, 20, 1, 2),
    "b1": (11, 0, 10, 0, 10, 2, 3),
    "b2": (12, 200, 210, 0, 10, 2, 4),
    "b3": (13, 10, 20, 10, 20, 2, 5),
}
DATASETS = {
    "A": ["a1", "a2", "a3", "a4"],
    "B": ["b1", "b2"],
    "C": ["b1", "b2", "b3"],
}


@pytest.fixture(scope="module")
def touching(temporal_module_session):
    """The maps and datasets of the table above"""
    tools = Tools(session=temporal_module_session, overwrite=True)
    specs = {}
    for name, (_, west, east, south, north, first, last) in MAPS.items():
        ring = [
            (west, south),
            (east, south),
            (east, north),
            (west, north),
            (west, south),
        ]
        body = "B 5\n" + "".join(f" {x} {y}\n" for x, y in ring)
        body += f"C 1 1\n {(west + east) / 2} {(south + north) / 2}\n 1 1\n"
        tools.v_in_ascii(
            input=StringIO(body), output=name, format="standard", flags="n"
        )
        specs[name] = MapSpec(name, None, day(first - 1), day(last - 1))
    for stds, names in DATASETS.items():
        register_stds(tools, "stvds", stds, [specs[name] for name in names])
    return temporal_module_session


def stamped(expression, runner):
    """The (start, end) of the maps that -s makes of the expression, sorted"""
    result = outcome(KIND, expression, RUNNERS[runner], spatial=True)
    assert "error" not in result, result
    return sorted((row[1][:10], row[2][:10]) for row in result["maps"])


def test_inverse_selection_keeps_a_map_without_a_related_partner_as_it_is(touching):
    # a1 is related to b1: same box, and a1 precedes b1 because 01.-02. ends
    # where 02.-03. begins. It is dropped. a2 precedes b1 and b2 in time, but
    # their boxes are 90 and 190 units away. a3 follows both. a4 precedes b1
    # in time but shares only the corner (10, 10) with it, which is no spatial
    # relation. None of the three has a related partner, so each keeps its
    # own time.
    assert stamped("A {!:,precedes,r} B", "classic") == [
        ("2001-01-01", "2001-01-02"),
        ("2001-01-01", "2001-01-02"),
        ("2001-01-05", "2001-01-06"),
    ]


def test_the_reference_stamps_a_touching_partner(touching):
    # The reference keeps a4 for the same reason as the classic profile, but
    # stamps it with the time of b1, whose box touches that of a4 only.
    # Measured 23.10.2026 with this test; the hand value is the one of the
    # profile above.
    assert stamped("A {!:,precedes,r} B", "reference") == [
        ("2001-01-01", "2001-01-02"),
        ("2001-01-02", "2001-01-03"),
        ("2001-01-05", "2001-01-06"),
    ]


def test_the_core_refuses_a_time_operator_other_than_l_in_an_inverse_selection(
    touching,
):
    result = outcome(KIND, "A {!:,precedes,r} B", RUNNERS["core"], spatial=True)
    assert result["error"] == "SyntaxError"


@pytest.mark.parametrize("runner", ["classic", "core"])
@pytest.mark.parametrize(
    ("operator", "a1", "a4"),
    [
        # a1 has b1 as its only related partner: same box, a1 precedes b1.
        # b3 shares only the corner (10, 10) with a1, b2 is 190 units away.
        # a4 has b3 as its only related partner: same box, a4 (01.-02.)
        # precedes b3 (02.-05.). b1 touches a4 at the corner only. r takes
        # the time of the partner; u joins the time of the map and the
        # partner. a2 (far from every B map) and a3 (no precedes) are left out.
        ("r", ("2001-01-02", "2001-01-03"), ("2001-01-02", "2001-01-05")),
        ("u", ("2001-01-01", "2001-01-03"), ("2001-01-01", "2001-01-05")),
    ],
)
def test_selection_takes_the_time_of_related_partners_only(
    touching, runner, operator, a1, a4
):
    assert stamped(f"A {{:,precedes,{operator}}} C", runner) == [
        a1,
        a4,
    ]


@pytest.mark.parametrize(
    ("operator", "a1"),
    [
        ("r", ("2001-01-02", "2001-01-05")),
        ("u", ("2001-01-01", "2001-01-05")),
    ],
)
def test_the_reference_stamps_a_touching_partner_in_a_selection(touching, operator, a1):
    # The reference gives a1 the time of b3, whose box touches that of a1 at
    # a corner, instead of the time of b1. Measured 23.10.2026 with this test.
    result = stamped(f"A {{:,precedes,{operator}}} C", "reference")
    assert result[0] == a1
