"""Tests for the topology links that a map keeps to its related maps

Two maps are equal only if they are the same object, whatever their
identifiers say, so a link is entered once per object. The relation lists
keep the order in which the links were entered, and so does the dictionary of
relations: a consumer that walks them sees a stable order.
"""

import contextlib
import io

import pytest

from grass.temporal import RasterDataset
from grass.temporal.spatio_temporal_relationships import (
    set_spatial_relationship,
    set_temporal_relationship,
)

# The topology links need no database, but the datasets look up the session
# when they are built.
pytestmark = pytest.mark.usefixtures("temporal_module_session")

# relation given to set_temporal_relationship(a, b, relation), the relation
# dictionaries of a and of b with identifiers instead of maps
TEMPORAL = [
    ("equal", {"EQUAL": ["b@p"]}, {"EQUAL": ["a@p"]}),
    ("equals", {"EQUAL": ["b@p"]}, {"EQUAL": ["a@p"]}),
    ("follows", {"PRECEDES": ["b@p"]}, {"FOLLOWS": ["a@p"]}),
    ("precedes", {"FOLLOWS": ["b@p"]}, {"PRECEDES": ["a@p"]}),
    ("during", {"CONTAINS": ["b@p"]}, {"DURING": ["a@p"]}),
    (
        "starts",
        {"CONTAINS": ["b@p"], "STARTED": ["b@p"]},
        {"DURING": ["a@p"], "STARTS": ["a@p"]},
    ),
    (
        "finishes",
        {"CONTAINS": ["b@p"], "FINISHED": ["b@p"]},
        {"DURING": ["a@p"], "FINISHES": ["a@p"]},
    ),
    ("contains", {"DURING": ["b@p"]}, {"CONTAINS": ["a@p"]}),
    (
        "started",
        {"DURING": ["b@p"], "STARTS": ["b@p"]},
        {"CONTAINS": ["a@p"], "STARTED": ["a@p"]},
    ),
    (
        "finished",
        {"DURING": ["b@p"], "FINISHES": ["b@p"]},
        {"CONTAINS": ["a@p"], "FINISHED": ["a@p"]},
    ),
    ("overlaps", {"OVERLAPPED": ["b@p"]}, {"OVERLAPS": ["a@p"]}),
    ("overlapped", {"OVERLAPS": ["b@p"]}, {"OVERLAPPED": ["a@p"]}),
    ("before", {}, {}),
    ("after", {}, {}),
    ("None", {}, {}),
]

SPATIAL = [
    ("equivalent", {"EQUIVALENT": ["b@p"]}, {"EQUIVALENT": ["a@p"]}),
    ("overlap", {"OVERLAP": ["b@p"]}, {"OVERLAP": ["a@p"]}),
    ("meet", {"MEET": ["b@p"]}, {"MEET": ["a@p"]}),
    ("contain", {"IN": ["b@p"]}, {"CONTAIN": ["a@p"]}),
    ("in", {"CONTAIN": ["b@p"]}, {"IN": ["a@p"]}),
    ("cover", {"COVERED": ["b@p"]}, {"COVER": ["a@p"]}),
    ("covered", {"COVER": ["b@p"]}, {"COVERED": ["a@p"]}),
    ("bogus", {}, {}),
    ("None", {}, {}),
]


def ids(relations):
    """Return the dictionary of relations with identifiers instead of maps"""
    return {
        key: [m.get_id() for m in value] if isinstance(value, list) else value.get_id()
        for key, value in relations.items()
    }


def printed(function):
    """Return what a function prints"""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        function()
    return buffer.getvalue()


@pytest.mark.parametrize(("relation", "of_a", "of_b"), TEMPORAL)
def test_the_temporal_relation_links_both_maps(relation, of_a, of_b):
    a, b = RasterDataset("a@p"), RasterDataset("b@p")

    set_temporal_relationship(a, b, relation)

    assert ids(a.get_temporal_relations()) == of_a
    assert ids(b.get_temporal_relations()) == of_b
    # The order of the keys is the order of the links, not an alphabetical one.
    assert list(a.get_temporal_relations()) == list(of_a)


@pytest.mark.parametrize(("relation", "of_a", "of_b"), SPATIAL)
def test_the_spatial_relation_links_both_maps(relation, of_a, of_b):
    a, b = RasterDataset("a@p"), RasterDataset("b@p")

    set_spatial_relationship(a, b, relation)

    assert ids(a.get_spatial_relations()) == of_a
    assert ids(b.get_spatial_relations()) == of_b
    assert list(a.get_spatial_relations()) == list(of_a)


def test_the_same_pair_is_linked_once():
    a, b = RasterDataset("a@p"), RasterDataset("b@p")

    for _ in range(3):
        set_temporal_relationship(a, b, "starts")
        set_spatial_relationship(a, b, "cover")

    assert ids(a.get_temporal_relations()) == {
        "CONTAINS": ["b@p"],
        "STARTED": ["b@p"],
    }
    assert ids(a.get_spatial_relations()) == {"COVERED": ["b@p"]}


def test_maps_with_the_same_identifier_are_different_maps():
    a = RasterDataset("a@p")
    first, second = RasterDataset("x@p"), RasterDataset("x@p")

    set_temporal_relationship(a, first, "follows")
    set_temporal_relationship(a, second, "follows")

    assert a.get_precedes() == [first, second]
    assert ids(a.get_temporal_relations()) == {"PRECEDES": ["x@p", "x@p"]}


def test_a_map_is_not_equal_to_itself_as_a_relation():
    a = RasterDataset("a@p")

    set_temporal_relationship(a, a, "equal")
    set_spatial_relationship(a, a, "equivalent")

    assert a.get_temporal_relations() == {}
    assert a.get_spatial_relations() == {}


def test_the_links_keep_the_order_of_their_entry():
    a = RasterDataset("a@p")
    partners = [RasterDataset(f"p{i}@p") for i in (3, 1, 2)]

    for partner in partners:
        set_temporal_relationship(a, partner, "during")

    assert a.get_contains() == partners


def test_a_missing_relation_is_none_and_the_dictionary_is_a_copy():
    a, b = RasterDataset("a@p"), RasterDataset("b@p")
    set_temporal_relationship(a, b, "precedes")

    assert a.get_equal() is None
    assert a.get_follows() == [b]
    relations = a.get_temporal_relations()
    relations["EQUAL"] = []
    assert a.get_equal() is None
    assert relations["FOLLOWS"] is a.get_follows()


def test_next_and_prev_are_entered_among_the_relations():
    a, b, c = (RasterDataset(f"{n}@p") for n in "abc")
    assert (a.next(), a.prev()) == (None, None)

    set_temporal_relationship(a, b, "equal")
    a.set_next(b)
    a.set_prev(c)

    assert (a.next(), a.prev()) == (b, c)
    assert list(a.get_temporal_relations()) == ["EQUAL", "NEXT", "PREV"]


def test_reset_forgets_every_link():
    a, b = RasterDataset("a@p"), RasterDataset("b@p")
    set_temporal_relationship(a, b, "equal")
    set_spatial_relationship(a, b, "meet")
    a.set_next(b)
    a.set_topology_build_true()

    a.reset_topology()

    assert a.get_temporal_relations() == {}
    assert a.get_spatial_relations() == {}
    assert a.next() is None
    assert a.is_topology_build() == {"spatial": False, "temporal": False}


def test_the_numbers_of_the_temporal_relations():
    a = RasterDataset("a@p")
    assert a.get_number_of_temporal_relations() is None
    for name in ("x", "y"):
        set_temporal_relationship(RasterDataset(name + "@p"), a, "overlaps")
    a.set_temporal_topology_build_true()

    assert a.get_number_of_temporal_relations() == {
        "equal": 0,
        "follows": 0,
        "precedes": 0,
        "overlaps": 2,
        "overlapped": 0,
        "during": 0,
        "contains": 0,
        "starts": 0,
        "started": 0,
        "finishes": 0,
        "finished": 0,
    }
    assert a.get_number_of_relations() == a.get_number_of_temporal_relations()


def test_the_numbers_of_the_spatial_relations():
    a = RasterDataset("a@p")
    assert a.get_number_of_spatial_relations() is None
    set_spatial_relationship(RasterDataset("x@p"), a, "in")
    a.set_spatial_topology_build_true()

    assert a.get_number_of_spatial_relations() == {
        "equivalent": 0,
        "overlap": 0,
        "in": 1,
        "contain": 0,
        "meet": 0,
        "cover": 0,
        "covered": 0,
    }


def crowded():
    """A map with all relations; during and overlap have more than three maps"""
    m = RasterDataset("m@p")
    counts = {"during": 4, "contains": 1}
    for relation in [
        "equal",
        "follows",
        "precedes",
        "overlaps",
        "overlapped",
        "during",
        "contains",
        "starts",
        "started",
        "finishes",
        "finished",
    ]:
        for i in range(counts.get(relation, 1)):
            set_temporal_relationship(RasterDataset(f"{relation}_{i}@p"), m, relation)
    m.set_next(RasterDataset("n@p"))
    m.set_prev(RasterDataset("q@p"))
    for relation in [
        "equivalent",
        "overlap",
        "meet",
        "contain",
        "in",
        "cover",
        "covered",
    ]:
        for i in range(4 if relation == "overlap" else 1):
            set_spatial_relationship(RasterDataset(f"{relation}_{i}@p"), m, relation)
    return m


TEMPORAL_INFO = """\
 +-------------------- Temporal Topology -------------------------------------+
 | Next: ...................... n@p
 | Previous: .................. q@p
 | Equal:...................... equal_0@p
 | Follows: ................... follows_0@p
 | Precedes: .................. precedes_0@p
 | Overlaps: .................. overlaps_0@p
 | Overlapped: ................ overlapped_0@p
 | During: .................... during_0@p,during_1@p,during_2@p
 | ............................ during_3@p,starts_0@p,finishes_0@p
 | Contains: .................. contains_0@p,started_0@p,finished_0@p
 | Starts:.. .................. starts_0@p
 | Started:. .................. started_0@p
 | Finishes:................... finishes_0@p
 | Finished:................... finished_0@p
"""

SPATIAL_INFO = """\
 +-------------------- Spatial Topology --------------------------------------+
 | Equivalent: ................ equivalent_0@p
 | Cover: ..................... cover_0@p
 | Covered: ................... covered_0@p
 | Overlap: ................... overlap_0@p,overlap_1@p,overlap_2@p
 | ............................ overlap_3@p
 | In: ........................ in_0@p
 | Contain: ................... contain_0@p
 | Meet: ...................... meet_0@p
"""


def test_the_temporal_topology_is_printed_in_the_order_of_the_table():
    assert printed(crowded().print_temporal_topology_info) == TEMPORAL_INFO


def test_the_spatial_topology_is_printed_in_the_order_of_the_table():
    assert printed(crowded().print_spatial_topology_info) == SPATIAL_INFO


def test_a_map_without_links_prints_only_the_header():
    a = RasterDataset("a@p")

    assert printed(a.print_temporal_topology_info) == TEMPORAL_INFO.splitlines(True)[0]
    assert printed(a.print_temporal_topology_shell_info) == ""
    assert printed(a.print_spatial_topology_shell_info) == ""


def test_the_numbers_of_both_topologies_are_one_dictionary():
    a = RasterDataset("a@p")
    set_temporal_relationship(RasterDataset("x@p"), a, "equal")
    set_spatial_relationship(RasterDataset("y@p"), a, "meet")
    a.set_topology_build_true()

    numbers = a.get_number_of_relations()

    assert numbers == {
        **a.get_number_of_temporal_relations(),
        **a.get_number_of_spatial_relations(),
    }
    assert (numbers["equal"], numbers["meet"], numbers["follows"]) == (1, 1, 0)


def test_the_numbers_of_the_spatial_topology_alone():
    a = RasterDataset("a@p")
    set_spatial_relationship(RasterDataset("y@p"), a, "meet")
    a.set_spatial_topology_build_true()

    assert a.get_number_of_relations() == a.get_number_of_spatial_relations()


def test_there_are_no_numbers_without_a_topology():
    assert RasterDataset("a@p").get_number_of_relations() is None
