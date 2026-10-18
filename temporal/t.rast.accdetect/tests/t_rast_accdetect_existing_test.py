"""Test t.rast.accdetect with existing results and with qualified names"""

import itertools

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

OPTIONS = {"start": "2001-01-01", "cycle": "6 days", "range": "10,50"}


def test_the_results_may_be_named_with_the_mapset(tools, cells, by_day):
    tools.t_rast_accdetect(
        input=cells,
        occurrence="qual_occ@PERMANENT",
        indicator="qual_ind@PERMANENT",
        basename="qual",
        **OPTIONS,
    )

    assert sorted(by_day("qual_occ")) == [0, 1, 2, 3, 4]
    assert sorted(by_day("qual_ind")) == [0, 1, 2, 3, 4]


def test_overwrite_replaces_both_datasets(tools, cells, by_day):
    options = {"input": cells, "occurrence": "ov_occ", "indicator": "ov_ind", **OPTIONS}
    tools.t_rast_accdetect(basename="ov", **options)
    assert sorted(by_day("ov_occ")) == [0, 1, 2, 3, 4]

    # With the range 25 to 45 only the days 1 to 4 have a value.
    tools.t_rast_accdetect(
        basename="ov", overwrite=True, **{**options, "range": "25,45"}
    )

    assert sorted(by_day("ov_occ")) == [1, 2, 3, 4]
    assert sorted(by_day("ov_ind")) == [1, 2, 3, 4]
    assert stds_info(tools, "strds", "ov_occ")["number_of_maps"] == 4


_taken = itertools.count()


@pytest.fixture
def taken(tools, cells):
    """A basename whose first occurrence and indicator maps exist elsewhere

    Each test gets its own name: the maps live in the mapset of the module and
    an overwrite run would otherwise leave a map to the next test.
    """
    base = f"tk{next(_taken)}"
    create_stds(
        tools,
        "strds",
        f"{base}_other",
        [
            MapSpec(f"{base}_2001_01_01", 7, day(40), day(41)),
            MapSpec(f"{base}_indicator_2001_01_01", 7, day(41), day(42)),
        ],
    )
    return base


def _detect(tools, cells, base, **options):
    return tools.t_rast_accdetect(
        input=cells,
        occurrence=f"{base}_occ",
        indicator=f"{base}_ind",
        basename=base,
        **{**OPTIONS, **options},
    )


def test_an_occurrence_map_that_is_registered_elsewhere_is_not_replaced(
    tools, cells, taken
):
    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=cells, occurrence=f"{taken}_occ", basename=taken, **OPTIONS
        )

    assert (
        f"Map <{taken}_2001_01_01@PERMANENT> is already registered in the "
        "temporal database, use overwrite flag to overwrite" in message(error.value)
    )


def test_an_indicator_map_that_is_registered_elsewhere_is_not_replaced(tools, cells):
    # Only the indicator name is taken: the occurrence maps come out fine.
    name = "tk_ind_only_indicator_2001_01_01"
    create_stds(tools, "strds", "tk_ind_only", [MapSpec(name, 7, day(40), day(41))])

    with pytest.raises(ToolError) as error:
        _detect(tools, cells, "tk_ind_only")

    assert (
        f"Map <{name}@PERMANENT> is already registered in the temporal "
        "database, use overwrite flag to overwrite" in message(error.value)
    )


def test_overwrite_replaces_a_result_map_that_is_registered_elsewhere(
    tools, cells, taken
):
    _detect(tools, cells, taken, overwrite=True)

    assert [r.name for r in list_maps(tools, "strds", f"{taken}_occ")][0] == (
        f"{taken}_2001_01_01"
    )
    assert [r.name for r in list_maps(tools, "strds", f"{taken}_ind")][0] == (
        f"{taken}_indicator_2001_01_01"
    )
    # The maps leave the list of the other dataset.
    assert list_maps(tools, "strds", f"{taken}_other") == []


@pytest.mark.xfail(
    strict=True,
    reason="The counter of the other dataset keeps the replaced maps (2, not 0).",
)
def test_the_other_dataset_counts_its_maps_after_an_overwrite(tools, cells, taken):
    _detect(tools, cells, taken, overwrite=True)

    assert stds_info(tools, "strds", f"{taken}_other")["number_of_maps"] == 0
