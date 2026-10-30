"""The public parser classes are separate from the reference implementation

The classes that t.rast.algebra, t.rast3d.algebra, t.vect.algebra and the
addons call do not inherit from the parser classes of the reference
implementation (grass.temporal.classic), and they build an object of the
reference only when something needs one. These tests run without a database:
a facade that needed the reference at construction or in ``parse()`` of the
core would fail here.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import copy
import pickle

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser import facade
from grass.temporal.classic import temporal_algebra as reference

CLASSES = [
    ("TemporalRasterAlgebraParser", facade.TemporalRasterAlgebraParser),
    ("TemporalRaster3DAlgebraParser", facade.TemporalRaster3DAlgebraParser),
    ("TemporalVectorAlgebraParser", facade.TemporalVectorAlgebraParser),
]


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_the_package_exports_the_facade(name, parser_class):
    assert getattr(tgis, name) is parser_class


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_a_facade_is_not_an_engine(name, parser_class):
    assert not issubclass(parser_class, reference.TemporalAlgebraParser)
    assert not isinstance(parser_class(), reference.TemporalAlgebraParser)


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_construction_builds_no_engine(name, parser_class):
    parser = parser_class(run=True, debug=False)
    assert parser._reference_object is None
    assert (parser.run, parser.debug, parser.use_granularity) == (True, False, False)
    assert parser.granularity is None


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_the_defaults_are_those_of_the_classes_before_the_engine_was_separated(
    name, parser_class
):
    parser = parser_class()
    assert (parser.run, parser.debug, parser.spatial) == (False, True, False)
    assert parser.classic is None


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_a_facade_lists_the_names_of_the_engine(name, parser_class):
    names = dir(parser_class())
    assert {"parse", "setup_common_granularity"} <= set(names)
    assert set(dir(parser_class._reference_class)) <= set(names)


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_a_facade_can_be_copied_and_pickled(name, parser_class):
    parser = parser_class(run=True, debug=False, classic=True)
    for clone in (
        copy.copy(parser),
        copy.deepcopy(parser),
        pickle.loads(pickle.dumps(parser)),  # noqa: S301, our own object
    ):
        assert (clone.run, clone.debug, clone.classic) == (True, False, True)
        assert clone._reference_object is None


def test_an_unknown_name_with_an_underscore_does_not_build_an_engine():
    parser = facade.TemporalRasterAlgebraParser()
    with pytest.raises(AttributeError):
        parser._no_such_attribute  # noqa: B018
    assert parser._reference_object is None


class StubReference:
    """Stands in for the reference, which needs a database"""

    def __init__(self, **arguments):
        self.arguments = arguments
        self.granularity = None
        self.use_granularity = False
        self.calls = []
        self.names = {"x": 1}

    def setup_common_granularity(self, expression, stdstype, lexer):
        self.calls.append((expression, stdstype, lexer))
        self.granularity = "1 day"
        self.use_granularity = True
        return True


class StubbedParser(facade.TemporalRasterAlgebraParser):
    _reference_class = StubReference


def test_the_granularity_mode_goes_to_one_engine_with_the_options_of_the_facade():
    parser = StubbedParser(pid=7, run=True, debug=False, nprocs=3, time_suffix="gran")
    assert parser.setup_common_granularity("R = A + B", "strds", "lexer") is True
    reference_object = parser._reference_object
    assert reference_object.calls == [("R = A + B", "strds", "lexer")]
    assert reference_object.arguments == {
        "pid": 7,
        "run": True,
        "debug": False,
        "spatial": False,
        "register_null": False,
        "dry_run": False,
        "nprocs": 3,
        "time_suffix": "gran",
    }
    assert (parser.granularity, parser.use_granularity) == ("1 day", True)
    # The same reference object answers later calls.
    parser.setup_common_granularity("R = A + B")
    assert parser._reference_object is reference_object


def test_options_set_after_the_construction_reach_the_engine():
    parser = StubbedParser(run=False)
    parser.setup_common_granularity("R = A + B")
    parser.run = True
    parser.setup_common_granularity("R = A + B")
    assert parser._reference_object.run is True


def test_a_name_only_the_engine_has_is_read_from_it():
    parser = StubbedParser()
    assert parser.names == {"x": 1}
    assert parser._reference_object is not None
