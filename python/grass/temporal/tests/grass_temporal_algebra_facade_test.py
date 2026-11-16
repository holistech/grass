"""The public parser classes of the algebra core

The classes that t.rast.algebra, t.rast3d.algebra, t.vect.algebra and the
addons call keep the options of their constructor as attributes and compute
with the core. These tests run without a database.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import copy
import pickle

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser import facade

CLASSES = [
    ("TemporalRasterAlgebraParser", facade.TemporalRasterAlgebraParser),
    ("TemporalRaster3DAlgebraParser", facade.TemporalRaster3DAlgebraParser),
    ("TemporalVectorAlgebraParser", facade.TemporalVectorAlgebraParser),
]


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_the_package_exports_the_facade(name, parser_class):
    assert getattr(tgis, name) is parser_class


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_construction_keeps_the_options(name, parser_class):
    parser = parser_class(run=True, debug=False)
    assert (parser.run, parser.debug, parser.use_granularity) == (True, False, False)
    assert parser.granularity is None


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_the_defaults_are_those_of_the_classes_before_the_core_replaced_them(
    name, parser_class
):
    parser = parser_class()
    assert (parser.run, parser.debug, parser.spatial) == (False, True, False)


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_a_facade_can_be_copied_and_pickled(name, parser_class):
    parser = parser_class(run=True, debug=False)
    for clone in (
        copy.copy(parser),
        copy.deepcopy(parser),
        pickle.loads(pickle.dumps(parser)),  # noqa: S301, our own object
    ):
        assert (clone.run, clone.debug) == (True, False)


@pytest.mark.parametrize(("name", "parser_class"), CLASSES)
def test_an_unknown_name_is_an_attribute_error(name, parser_class):
    with pytest.raises(AttributeError):
        parser_class().no_such_attribute  # noqa: B018


def test_the_granularity_mode_finds_the_datasets_in_the_syntax_tree(monkeypatch):
    """The core finds the datasets in its syntax tree and asks the library"""
    calls = []

    def common_granularity(names, stds_type):
        calls.append((names, stds_type))
        return "2 days"

    monkeypatch.setattr(facade, "common_granularity", common_granularity)
    parser = facade.TemporalRasterAlgebraParser()
    assert parser.setup_common_granularity("R = if(A != 1, B)", "str3ds") is True
    assert calls == [(["A", "B"], "str3ds")]
    assert (parser.granularity, parser.use_granularity) == ("2 days", True)
