"""sample_stds_by_stds_topology(): the map matrix and the printed table

v.what.strds, t.vect.observe.strds and the addon v.strds.stats take the
granules of a sampler dataset and the maps of the input datasets that are
related to each granule from this function. The tests fix what it returns for
every sampling method with and without the spatial check, for a sampler with a
gap, and for inputs with a map of the same time as a granule (the case in which
"start" lists nothing, because the classic function appends the relation
"equals", which no map ever has), maps that start together with a granule,
overlap it, lie in it, and an instant. The expected values are in
data/sampling_stds_characterization.json; they were taken from the function
before it was rebuilt on grass.temporal.related_maps, and checked against the
rules in its docstring.
"""

import json
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.related_maps import method_relations
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

EXPECTED = json.loads(
    (Path(__file__).parent / "data" / "sampling_stds_characterization.json").read_text()
)

# Days of January 2001, (start, end); end None is an instant. The sampler has
# a gap from day 3 to day 5. The boxes are (west, east, south, north) on a
# coarse grid, so that some touch at an edge or a corner.
SAMPLER = [
    ("s1", 0, 2, (0, 20, 0, 20)),
    ("s2", 2, 3, (20, 30, 0, 10)),
    ("s3", 5, 7, (0, 10, 30, 40)),
    ("s4", 7, 8, (10, 20, 30, 40)),
]
INPUT = [
    ("a", 0, 2, (0, 10, 0, 10)),  # equal to s1
    ("b", 1, 2, (10, 20, 10, 20)),  # in s1, ends with it
    ("c", 2, 4, (30, 40, 0, 10)),  # starts with s2, runs into the gap
    ("d", 4, 5, (0, 10, 30, 40)),  # in the gap
    ("e", 5, 7, (20, 30, 20, 30)),  # equal to s3
    ("f", 6, None, (0, 10, 30, 40)),  # an instant in s3
    ("g", 7, 9, (10, 20, 30, 40)),  # starts with s4, runs past it
    ("h", 4, 6, (0, 10, 30, 40)),  # overlaps the gap and s3
]
OTHER = [
    ("p", 0, 2, (0, 10, 0, 10)),
    ("q", 5, 7, (0, 10, 30, 40)),
]
RELATIVE_SAMPLER = [
    ("s1", 0, 2, (0, 20, 0, 20)),
    ("s2", 4, 6, (20, 30, 0, 10)),
]
RELATIVE_INPUT = [
    ("a", 0, 2, (0, 10, 0, 10)),
    ("b", 1, None, (10, 20, 10, 20)),
    ("c", 5, 8, (30, 40, 0, 10)),
]
METHODS = [
    ["start"],
    ["during"],
    ["overlap"],
    ["contain"],
    ["equal"],
    ["follows"],
    ["precedes"],
    ["contain", "start"],
    ["precedes", "follows", "overlap"],
    ["during", "overlap", "contain", "equal"],
]


NAMES = json.loads(
    (Path(__file__).parent / "data" / "sampling_stds_names.json").read_text()
)
# Names that the function accepted before it was rebuilt, besides the values of
# the option: the relations of the topology builder, in any case and with white
# space, "over" for "overlap", and "equals", which selects nothing. The expected
# values come from the function of the commit before the rebuild.
ACCEPTED = [key.split("|") for key in NAMES["matrix"]]


def day(number):
    return f"2001-01-{number + 1:02d}"


def build(tools, tmp_path, dataset, spans, relative=False):
    """One strds of raster maps with the given day spans and boxes"""
    lines = []
    for name, start, end, (west, east, south, north) in spans:
        tools.g_region(w=west, e=east, s=south, n=north, res=10)
        tools.r_mapcalc(expression=f"{dataset}_{name} = 1", overwrite=True)
        stamp = str if relative else day
        end_text = "" if end is None else f"|{stamp(end)}"
        lines.append(f"{dataset}_{name}|{stamp(start)}{end_text}")
    tools.t_create(
        type="strds",
        output=dataset,
        temporaltype="relative" if relative else "absolute",
        title=dataset,
        description=dataset,
        overwrite=True,
    )
    # Instants and intervals in separate files, as a file that mixes them
    # takes the end of the previous line for an instant
    for kind, kept in (
        ("instants", [x for x in lines if x.count("|") == 1]),
        ("intervals", [x for x in lines if x.count("|") == 2]),
    ):
        if kept:
            file = tmp_path / f"{dataset}_{kind}.txt"
            file.write_text("\n".join(kept) + "\n")
            units = {"unit": "days"} if relative else {}
            tools.t_register(
                type="raster", input=dataset, file=file, overwrite=True, **units
            )


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("sampling_stds")
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    build(tools, tmp_path, "smp", SAMPLER)
    build(tools, tmp_path, "inp", INPUT)
    build(tools, tmp_path, "oth", OTHER)
    build(tools, tmp_path, "rsm", RELATIVE_SAMPLER, relative=True)
    build(tools, tmp_path, "rin", RELATIVE_INPUT, relative=True)
    tools.t_create(
        type="strds",
        output="nothing",
        temporaltype="absolute",
        title="nothing",
        description="nothing",
        overwrite=True,
    )
    return tools


def described(map_):
    """What a caller can read from a map object of the matrix"""
    start, end = map_.get_temporal_extent_as_tuple()
    return [
        map_.get_id(),
        str(start),
        str(end),
        list(map_.get_spatial_extent_as_tuple()),
        map_.get_temporal_type(),
        map_.get_relative_time_unit(),
    ]


def matrix_of(matrices):
    return [
        [
            {
                "granule": described(entry["granule"]),
                "samples": [described(sample) for sample in entry["samples"]],
            }
            for entry in matrix
        ]
        for matrix in matrices
    ]


def sample(inputs, method, spatial):
    return tgis.sample_stds_by_stds_topology(
        "strds", "strds", inputs, "smp", False, None, method, spatial, False
    )


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("method", METHODS, ids="-".join)
def test_the_map_matrix(datasets, method, spatial):
    result = matrix_of(sample(["inp", "oth"], method, spatial))

    assert result == EXPECTED["matrix"]["|".join(method)][str(spatial)]


@pytest.mark.parametrize("method", [["equal"], ["start", "during"], ["overlap"]])
def test_relative_time(datasets, method):
    result = matrix_of(
        tgis.sample_stds_by_stds_topology(
            "strds", "strds", ["rin"], "rsm", False, None, method, False, False
        )
    )

    assert result == EXPECTED["relative"]["|".join(method)]


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("method", ACCEPTED, ids="-".join)
def test_a_name_that_was_accepted_before_gives_the_same_map_matrix(
    datasets, method, spatial
):
    result = matrix_of(sample(["inp", "oth"], method, spatial))

    assert result == NAMES["matrix"]["|".join(method)][str(spatial)]


@pytest.mark.parametrize("method", ACCEPTED, ids="-".join)
def test_a_name_that_was_accepted_before_gives_the_same_relative_matrix(
    datasets, method
):
    result = matrix_of(
        tgis.sample_stds_by_stds_topology(
            "strds", "strds", ["rin"], "rsm", False, None, method, False, False
        )
    )

    assert result == NAMES["relative"]["|".join(method)]


def test_the_methods_as_a_comma_separated_string(datasets):
    as_text = matrix_of(sample("inp", "equal,start", False))

    assert as_text == matrix_of(sample("inp", ["equal", "start"], False))


def test_equal_time_is_not_found_by_start(datasets):
    # The granule s1 and the map a are equal. "equal" lists a, "start" does not.
    equal = sample(["inp"], ["equal"], False)[0][0]["samples"]
    start = sample(["inp"], ["start"], False)[0][0]["samples"]

    assert [s.get_id() for s in equal][0].startswith("inp_a@")
    assert "inp_a" not in " ".join(str(s.get_id()) for s in start)


def test_an_input_without_maps_gives_a_granule_without_samples(datasets):
    result = matrix_of(sample(["nothing"], ["equal"], False))

    assert result == EXPECTED["nothing"]


def test_the_printed_table(datasets, capsys):
    result = tgis.sample_stds_by_stds_topology(
        "strds", "strds", "inp,oth", "smp", True, "|", "equal,start", False, True
    )

    assert result is not None
    assert capsys.readouterr().out.splitlines() == EXPECTED["printed"]


def test_a_comma_as_separator_is_replaced(datasets, capsys):
    tgis.sample_stds_by_stds_topology(
        "strds", "strds", "inp", "smp", True, ",", ["equal"], False, True
    )

    assert " | " in capsys.readouterr().out.splitlines()[0]


def test_a_sampler_with_points_is_refused(datasets, capsys):
    # The sampler must have interval time: "inp" has an instant
    result = tgis.sample_stds_by_stds_topology(
        "strds", "strds", ["smp"], "inp", False, None, ["equal"], False, False
    )

    assert result is None


def test_a_missing_dataset_stops(datasets):
    with pytest.raises(tgis.FatalError, match="not found"):
        tgis.sample_stds_by_stds_topology(
            "strds", "strds", ["missing"], "smp", False, None, ["equal"], False, False
        )
    with pytest.raises(tgis.FatalError, match="not found"):
        tgis.sample_stds_by_stds_topology(
            "strds", "strds", ["inp"], "missing", False, None, ["equal"], False, False
        )


@pytest.mark.parametrize("spatial", [False, True])
def test_an_unknown_method_selects_nothing_besides_the_known_ones(datasets, spatial):
    assert matrix_of(sample(["inp", "oth"], ["equal", "sideways"], spatial)) == (
        matrix_of(sample(["inp", "oth"], ["equal"], spatial))
    )


@pytest.mark.parametrize("method", [["sideways"], ["START"]])
@pytest.mark.parametrize("spatial", [False, True])
def test_an_unknown_method_selects_nothing(datasets, method, spatial):
    """Every granule gets one empty map with its own extent

    Taken 2026-10-26 from the function at b8f890df1c in a temporary project
    with the datasets of this module ("START" is no relation of the topology
    builder either: only the lower-case group name counts).
    """
    result = matrix_of(sample(["inp", "oth"], method, spatial))

    assert len(result) == 2
    for matrix in result:
        assert [entry["granule"][0] for entry in matrix] == [
            "smp_s1@PERMANENT",
            "smp_s2@PERMANENT",
            None,
            "smp_s3@PERMANENT",
            "smp_s4@PERMANENT",
        ]
        for entry in matrix:
            assert entry["samples"] == [[None, *entry["granule"][1:]]]


def test_the_strict_method_names_still_refuse_an_unknown_one():
    with pytest.raises(ValueError, match="Unknown sampling method <sideways>"):
        method_relations(["sideways"])
