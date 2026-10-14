"""The algebra core on vector maps: reading datasets, planning and
computing

The datasets are described in the vector_series fixture in conftest.py.
"""

import importlib
from types import SimpleNamespace

import pytest

import grass.temporal as tgis
import grass.temporal.algebra as ta
from grass.exceptions import FatalError
from grass.temporal.algebra.backends import ModuleCall
from grass.tools import Tools


def test_source_reads_a_space_time_vector_dataset(vector_series):
    series = ta.source("aa", stds_type="stvds")
    assert series.kind == "vector"
    assert [slot.origin for slot in series] == [f"aa{i}@PERMANENT" for i in range(1, 4)]
    # Vector maps have a spatial extent, which spatial relations need.
    assert series.slots[0].space.east == pytest.approx(10)


def test_source_map_reads_a_vector_map(vector_series):
    series = ta.source_map("ev", kind="vector")
    assert series.kind == "vector"
    assert series.slots[0].origin == "ev@PERMANENT"


def test_missing_vector_map(vector_series):
    with pytest.raises(FatalError, match=r"^Vector map <missing@PERMANENT> not found$"):
        ta.source_map("missing", kind="vector")


def test_unknown_dataset_type(vector_series):
    with pytest.raises(ValueError, match="stds_type"):
        ta.source("aa", stds_type="vector")


def _maps(name):
    dataset = tgis.open_old_stds(name, "stvds")
    rows = []
    for map_ in dataset.get_registered_maps_as_objects(order="start_time") or []:
        map_.select()
        rows.append((map_.get_id(), map_.metadata.get_number_of_areas()))
    return rows


def test_overlay_and_of_overlapping_squares(vector_series):
    aa = ta.source("aa", stds_type="stvds")
    ab = ta.source("ab", stds_type="stvds")
    ta.materialize(
        ta.gather(aa, ta.equal, ab, reduce=ta.fold("and")), "core_and", overwrite=True
    )
    # aa3 and ab3 do not overlap, so the third map is empty and left out.
    assert [areas for _, areas in _maps("core_and")] == [1, 1]


def test_selected_vector_maps_are_registered_not_copied(vector_series):
    aa = ta.source("aa", stds_type="stvds")
    ab = ta.source("ab", stds_type="stvds")
    ta.materialize(ta.select(aa, ta.equal, ab), "core_sel", basename="core_sel")
    assert [ident for ident, _ in _maps("core_sel")] == [
        f"aa{i}@PERMANENT" for i in range(1, 4)
    ]
    # A second run without overwrite fails only at the existing dataset,
    # not at the input maps, which exist by nature.
    with pytest.raises(FatalError, match="Space time dataset"):
        ta.materialize(ta.select(aa, ta.equal, ab), "core_sel", basename="core_sel")


def test_a_map_kept_in_two_slots_is_registered_once(vector_series, monkeypatch):
    wide = ta.source("wide", stds_type="stvds")
    aa = ta.source("aa", stds_type="stvds")
    # wide1 (days 1-3) is related to aa1 and aa2, so two slots keep wide1.
    kept = ta.pairs(wide, ta.relation("starts|started|finishes|finished"), aa)
    assert [slot.origin for slot in kept].count("wide1@PERMANENT") == 2
    # The messenger writes from a process forked before the test, out of
    # reach of capfd.
    warnings = []
    # The package exports the function materialize under the name of the
    # module, so a plain import would give the function.
    monkeypatch.setattr(
        importlib.import_module("grass.temporal.algebra.materialize"),
        "get_tgis_message_interface",
        lambda: SimpleNamespace(warning=warnings.append, percent=lambda *args: None),
    )
    ta.materialize(kept, "core_twice", overwrite=True)
    assert [ident for ident, _ in _maps("core_twice")] == [
        "wide1@PERMANENT",
        "wide2@PERMANENT",
    ]
    assert any("<wide1@PERMANENT>" in warning for warning in warnings)


def test_an_empty_input_map_is_never_removed(vector_series):
    tools = Tools(session=vector_series.session, overwrite=True)
    tools.v_edit(map="empty_in", tool="create")
    tools.t_create(
        output="emptyin",
        type="stvds",
        temporaltype="absolute",
        title="e",
        description="e",
    )
    tools.t_register(
        input="emptyin",
        type="vector",
        maps="empty_in",
        start="2001-01-01",
        end="2001-01-02",
    )
    ta.materialize(ta.source("emptyin", stds_type="stvds"), "core_keep", overwrite=True)
    assert tgis.VectorDataset("empty_in@PERMANENT").map_exists()


def test_an_input_map_without_areas_stops_the_overlay(vector_series):
    pa = ta.source("pa", stds_type="stvds")
    aa = ta.source("aa", stds_type="stvds")
    with pytest.raises(FatalError, match="has no areas"):
        ta.materialize(
            ta.gather(pa, ta.equal, aa, reduce=ta.fold("and")),
            "core_pts",
            overwrite=True,
        )


def test_an_input_map_without_areas_stops_the_overlay_also_when_kept(
    vector_series,
):
    pa = ta.source("pa", stds_type="stvds")
    aa = ta.source("aa", stds_type="stvds")
    # pa1 goes into the result unchanged and into an overlay; it is still an
    # input of the expression, not an intermediate map to drop quietly.
    overlaid = ta.gather(pa, ta.equal, aa, reduce=ta.fold("and"))
    with pytest.raises(FatalError, match="has no areas"):
        ta.materialize(ta.merge(pa, overlaid), "core_kept", overwrite=True)


def test_an_empty_intermediate_map_drops_the_result(vector_series, monkeypatch):
    aa = ta.source("aa", stds_type="stvds")
    ab = ta.source("ab", stds_type="stvds")
    ac = ta.source("ac", stds_type="stvds")
    first = ta.gather(aa, ta.equal, ab, reduce=ta.fold("and"))
    warnings = []
    monkeypatch.setattr(
        importlib.import_module("grass.temporal.algebra.materialize"),
        "get_tgis_message_interface",
        lambda: SimpleNamespace(warning=warnings.append, percent=lambda *args: None),
    )
    ta.materialize(
        ta.gather(first, ta.equal, ac, reduce=ta.fold("and")),
        "core_drop",
        overwrite=True,
    )
    # The first intersection of aa and ab overlaps the square of ac at x=0.
    # The second one lies at x=25 to 30, apart from both squares of ac, so
    # its overlay is computed and empty. The third intersection is empty, so
    # the overlay with ac has no areas to work on and that map is dropped
    # before it is computed.
    assert _maps("core_drop") == [("core_drop_0@PERMANENT", 1)]
    # The warning names the map the user misses, not only the temporary one.
    assert warnings == [
        "Result map <core_drop_2> is left out: intermediate map "
        "<core_drop_2_tmp0@PERMANENT> has no areas"
    ]


def test_a_missing_intermediate_map_is_an_error(vector_series):
    # v.overlay writes its output even when it is empty, so this guards an
    # invariant: a result map must not disappear without a message.
    materialize = importlib.import_module("grass.temporal.algebra.materialize")
    call = ModuleCall(
        "v.overlay",
        {
            "ainput": "nosuch_tmp0",
            "binput": "aa1@PERMANENT",
            "operator": "and",
            "output": "nosuch",
        },
    )
    with pytest.raises(FatalError, match=r"<nosuch_tmp0@PERMANENT>"):
        materialize._overlay_inputs_usable(call, {"nosuch_tmp0"}, "PERMANENT", "nosuch")


def test_buffer_of_points(vector_series):
    pa = ta.source("pa", stds_type="stvds")
    ta.materialize(ta.buffer(pa, 1, features="point"), "core_buf", overwrite=True)
    assert [areas for _, areas in _maps("core_buf")] == [1, 2, 3]


def test_vector_maps_are_computed_one_after_another(vector_series):
    aa = ta.source("aa", stds_type="stvds")
    with pytest.raises(ValueError, match="nprocs"):
        ta.materialize(ta.buffer(aa, 1), "core_par", overwrite=True, nprocs=2)


def _vparse(expression, name, **keywords):
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=False, **keywords)
    return parser.parse(f"{name} = {expression}", name, True)


def test_vector_parser_runs_the_core_with_classic_false(vector_series):
    _vparse("aa & ab", "fac_and", classic=False)
    assert [areas for _, areas in _maps("fac_and")] == [1, 1]


def test_vector_parser_registers_selected_maps(vector_series):
    chain = _vparse("aa : ab", "fac_sel", classic=False)
    assert [name for name, _, _ in chain["register"]] == [
        f"aa{i}@PERMANENT" for i in range(1, 4)
    ]


def test_vector_parser_buffers(vector_series):
    _vparse("buff_p(pa, 1)", "fac_buf", classic=False)
    assert [areas for _, areas in _maps("fac_buf")] == [1, 2, 3]


def test_an_empty_vector_result_creates_an_empty_dataset(vector_series):
    # The daily maps of aa never have the same time as the two-day maps of
    # wide, and the default relation is equal.
    _vparse("aa : wide", "fac_empty", classic=False)
    assert _maps("fac_empty") == []


def test_a_raster_dataset_is_not_a_vector_dataset(vector_series):
    tools = Tools(session=vector_series.session, overwrite=True)
    tools.r_mapcalc(expression="rmap2 = 1")
    tools.t_create(
        output="rast2",
        type="strds",
        temporaltype="absolute",
        title="r",
        description="r",
    )
    tools.t_register(input="rast2", maps="rmap2", start="2001-01-01", end="2001-01-02")
    with pytest.raises(
        FatalError, match=r"^Space time vector dataset <rast2@PERMANENT> not found$"
    ):
        _vparse("rast2 : aa", "fac_rast", classic=False)


def test_progress_counts_the_computed_vector_maps(vector_series, monkeypatch):
    """Every result map with calls is one step, also on the vector path"""
    reported = []
    monkeypatch.setattr(
        tgis.get_tgis_message_interface(),
        "percent",
        lambda current, total, step: reported.append((current, total)),
    )
    aa = ta.source("aa", stds_type="stvds")
    ab = ta.source("ab", stds_type="stvds")
    series = ta.gather(aa, ta.equal, ab, reduce=ta.fold("and"))
    computed = sum(
        1 for planned in ta.plan(series, "core_progress").maps if planned.calls
    )
    assert computed > 0
    ta.materialize(series, "core_progress", overwrite=True)
    assert reported == [(step, computed) for step in range(1, computed + 1)]
