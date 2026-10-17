"""The algebra core on 3D raster maps: reading datasets, planning and
computing

The datasets are described in the series_3d fixture in conftest.py.
"""

import pytest

import grass.temporal as tgis
import grass.temporal.algebra as ta
from grass.exceptions import FatalError
from grass.temporal.algebra.materialize import check_absent
from grass.tools import Tools


def test_source_reads_a_space_time_3d_raster_dataset(series_3d):
    series = ta.source("A", stds_type="str3ds")
    assert series.kind == "raster3d"
    assert [slot.origin for slot in series] == [f"a{i}@PERMANENT" for i in range(1, 5)]


def test_source_map_reads_a_3d_raster_map(series_3d):
    series = ta.source_map("single", kind="raster3d")
    assert series.kind == "raster3d"
    assert series.slots[0].extent is not None
    timeless = ta.source_map("single", timestamp=False, kind="raster3d")
    assert timeless.timeless


def test_source_does_not_read_a_dataset_of_another_type(series_3d):
    with pytest.raises(
        FatalError, match=r"^Space time raster dataset <A@PERMANENT> not found$"
    ):
        ta.source("A", stds_type="strds")


# W {:,contains,r} A in the core: w1 (100) for a1 and a2, w2 (200) for a3, a4
CORE_PAIRS = [(100, 100), (100, 100), (200, 200), (200, 200)]


def _values(name):
    dataset = tgis.open_old_stds(name, "str3ds")
    rows = []
    for map_ in dataset.get_registered_maps_as_objects(order="start_time"):
        map_.select()
        rows.append((map_.get_id(), map_.metadata.get_min(), map_.metadata.get_max()))
    return rows


def test_materialize_computes_3d_raster_maps(series_3d):
    a = ta.source("A", stds_type="str3ds")
    b = ta.source("B", stds_type="str3ds")
    ta.materialize(
        ta.gather(a, ta.equal, b, reduce=ta.fold("+")), "core_sum", overwrite=True
    )
    assert [row[1:] for row in _values("core_sum")] == [
        (11 * i, 11 * i) for i in range(1, 5)
    ]


def test_materialize_leaves_out_empty_3d_raster_maps(series_3d):
    a = ta.source("A", stds_type="str3ds")
    condition = ta.apply(">", a, 2)
    ta.materialize(ta.where(condition, a, None), "core_where", overwrite=True)
    assert [row[1] for row in _values("core_where")] == [3, 4]


def test_existing_3d_result_without_overwrite(series_3d):
    a = ta.source("A", stds_type="str3ds")
    ta.materialize(a, "core_once", basename="core_once", overwrite=True)
    with pytest.raises(FatalError, match="exists"):
        ta.materialize(a, "core_once", basename="core_once")


def test_check_absent_finds_existing_3d_maps(series_3d):
    a = ta.source("A", stds_type="str3ds")
    ta.materialize(a, "core_maps", basename="core_maps", overwrite=True)
    chain = ta.plan(a, "core_other", basename="core_maps")
    with pytest.raises(FatalError, match="exists"):
        check_absent(chain)


def _parse(expression, name, **keywords):
    parser = tgis.TemporalRaster3DAlgebraParser(run=True, debug=False, **keywords)
    return parser.parse(f"{name} = {expression}", name, True)


@pytest.mark.fixed_algebra
def test_parser_runs_the_core_with_classic_false(series_3d):
    _parse("A + B", "fac_sum", classic=False)
    assert [row[1] for row in _values("fac_sum")] == [11, 22, 33, 44]


@pytest.mark.fixed_algebra
def test_parser_samples_with_the_common_granularity(series_3d):
    """W has maps of two days; sampled by the day of A, w1 counts for days 1
    and 2, w2 for days 3 and 4"""
    parser = tgis.TemporalRaster3DAlgebraParser(run=True, debug=False, classic=False)
    assert parser.setup_common_granularity(
        expression="fac_gran = A + W",
        stdstype="str3ds",
        lexer=tgis.TemporalRasterAlgebraLexer(),
    )
    chain = parser.parse("fac_gran = A + W", "fac_gran", True)
    # Only the core quotes the names of the maps in the expression.
    assert dict(chain["processes"][0]["inputs"])["expression"] == (
        '"fac_gran_0"=("a1@PERMANENT" + "w1@PERMANENT")'
    )
    assert [row[1] for row in _values("fac_gran")] == [101, 102, 203, 204]


@pytest.mark.fixed_algebra
def test_parser_reads_3d_cell_offsets(series_3d):
    _parse("D[0,0,1]", "fac_offset", classic=False)
    # d holds the depth of each cell; one layer deeper the top layer reads
    # outside the region, which is null. Checked 2026-10-13 with r3.mapcalc
    # "o = d[0,0,1]" on the 3x3x3 region: min=2, max=3.
    assert [row[1:] for row in _values("fac_offset")][0] == (2, 3)


@pytest.mark.fixed_algebra
def test_a_raster_dataset_is_not_a_3d_dataset(series_3d):
    tools = Tools(session=series_3d.session, overwrite=True)
    tools.r_mapcalc(expression="flat = 1")
    tools.t_create(
        output="flat", type="strds", temporaltype="absolute", title="f", description="f"
    )
    tools.t_register(input="flat", maps="flat", start="2001-01-01", end="2001-01-02")
    with pytest.raises(
        FatalError, match=r"^Space time 3D raster dataset <flat@PERMANENT> not found$"
    ):
        _parse("flat + A", "fac_flat", classic=False)


@pytest.mark.fixed_algebra
def test_without_keyword_and_variable_the_parser_runs_the_core(series_3d, monkeypatch):
    monkeypatch.delenv("GRASS_TEMPORAL_ALGEBRA", raising=False)
    # A selection with the right reference gives one map per related pair in
    # the core: w1 (100) contains a1 and a2, w2 (200) contains a3 and a4.
    _parse("W {:,contains,r} A", "fac_default")
    assert [row[1:] for row in _values("fac_default")] == CORE_PAIRS


@pytest.mark.fixed_algebra
def test_an_empty_variable_runs_the_core(series_3d, monkeypatch):
    monkeypatch.setenv("GRASS_TEMPORAL_ALGEBRA", "")
    # The core gives one map per related pair, see above.
    _parse("W {:,contains,r} A", "fac_empty")
    assert [row[1:] for row in _values("fac_empty")] == CORE_PAIRS


@pytest.mark.fixed_algebra
def test_the_variable_selects_the_classic_algebra(series_3d, monkeypatch):
    monkeypatch.setenv("GRASS_TEMPORAL_ALGEBRA", "classic")
    # The classic algebra keeps only the last pair of each map of W.
    _parse("W {:,contains,r} A", "fac_variable")
    assert [row[1:] for row in _values("fac_variable")] == [(100, 100), (200, 200)]
