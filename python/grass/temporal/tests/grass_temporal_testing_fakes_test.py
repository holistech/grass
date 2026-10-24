"""Tests for the test-only caches of grass.temporal.testing.fakes

Each cached answer is compared with the answer of real IO, step by step
through the changes that could make it stale: another project, a changed
search path, a changed GISRC value and a temporal database created by a
subprocess. A cache that is wrong here would hide failures in all the tests
that run under it, so these tests switch the autouse caches off (real_io) and
install their own.
"""

import os
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal import core
import grass.pygrass.modules.interface.module as pygrass_module
from grass.pygrass.modules import Module
from grass.temporal.testing import fakes
from grass.temporal.testing.session import add_mapset, temporal_session

pytestmark = pytest.mark.real_io

BOOM = "boom"


def interface_state(name="r.mapcalc"):
    """Return the XML and the command line pygrass builds for a tool"""
    options = {"expression": "x = 1"} if name == "r.mapcalc" else {}
    module = Module(name, run_=False, **options)
    return module.xml, module.make_cmd()


def create_temporal_database_in(session, mapset):
    """Create a temporal database in another mapset with a subprocess"""
    gisenv = gs.gisenv(env=session.env)
    project = Path(gisenv["GISDBASE"]) / gisenv["LOCATION_NAME"]
    with gs.setup.init(project / mapset, env=os.environ.copy()) as other:
        gs.run_command(
            "t.create",
            output="made",
            type="strds",
            title="made",
            description="made",
            env=other.env,
        )


class TestMapsetsCache:
    def test_answers_equal_real_io_through_changes(self, tmp_path):
        """Cached and real answer of the mapset list agree after every change"""
        real = core.get_available_temporal_mapsets
        with fakes.mapsets_cache() as stats:
            cached = core.get_available_temporal_mapsets
            assert cached is not real
            with temporal_session(tmp_path / "a") as session:
                add_mapset(session, "second")
                for argument in (None, ".", "*"):
                    assert cached(argument) == real(argument)
                    assert cached(argument) == real(argument)
                assert stats.hits >= 3
                # The search path changes in the SEARCH_PATH file only.
                gs.run_command(
                    "g.mapsets", mapset="second", operation="add", env=session.env
                )
                for argument in (None, ".", "*"):
                    assert cached(argument) == real(argument)
                # A subprocess creates a temporal database in another mapset.
                create_temporal_database_in(session, "second")
                before = real("*")
                assert "second" in before
                assert cached("*") == before
                assert "second" in cached(None)
                gs.run_command(
                    "g.mapsets", mapset="second", operation="remove", env=session.env
                )
                for argument in (None, ".", "*"):
                    assert cached(argument) == real(argument)
            # Another project: same process, other GISRC.
            with temporal_session(tmp_path / "b") as session:
                for argument in (None, ".", "*"):
                    assert cached(argument) == real(argument)
                    assert cached(argument) == real(argument)

    def test_weak_key_goes_stale(self, tmp_path):
        """A key without the SEARCH_PATH state returns a removed mapset

        Negative test: shows that the comparison above sees a stale answer.
        """
        real = core.get_available_temporal_mapsets

        def weak(mapsets):
            return mapsets, os.environ.get("GISRC")

        with temporal_session(tmp_path / "a") as session:
            add_mapset(session, "second")
            create_temporal_database_in(session, "second")
            gs.run_command(
                "g.mapsets", mapset="second", operation="add", env=session.env
            )
            with fakes.mapsets_cache(key=weak):
                cached = core.get_available_temporal_mapsets
                assert "second" in cached(None)
                gs.run_command(
                    "g.mapsets", mapset="second", operation="remove", env=session.env
                )
                assert "second" not in real(None)
                assert "second" in cached(None)

    def test_key_without_database_files_goes_stale(self, tmp_path):
        """A key without the database files misses a database made by a subprocess

        Negative test for the third part of the key. The first answer has to
        be non-empty, otherwise it is not cached at all.
        """

        def without_databases(mapsets):
            return fakes.mapsets_key(mapsets)[:4]

        real = core.get_available_temporal_mapsets
        with temporal_session(tmp_path / "a") as session:
            add_mapset(session, "second")
            gs.run_command(
                "g.mapsets", mapset="second", operation="add", env=session.env
            )
            with fakes.mapsets_cache(key=without_databases):
                cached = core.get_available_temporal_mapsets
                assert "second" not in cached("*")
                create_temporal_database_in(session, "second")
                assert "second" in real("*")
                assert "second" not in cached("*")

    def test_not_cached_when_empty(self, tmp_path):
        """An empty answer is asked again every time"""
        with temporal_session(tmp_path / "a"), fakes.mapsets_cache() as stats:
            cached = core.get_available_temporal_mapsets
            # A mapset name that does not exist gives an empty answer.
            assert cached("nosuchmapset") == {}
            assert cached("nosuchmapset") == {}
            assert stats.hits == 0

    def test_cache_is_emptied_by_init(self, tmp_path):
        """init() through the module attribute clears the cache"""
        with temporal_session(tmp_path / "a"), fakes.mapsets_cache() as stats:
            cached = core.get_available_temporal_mapsets
            cached(None)
            cached(None)
            assert stats.hits == 1
            core.init()
            misses = stats.misses
            cached(None)
            assert stats.misses == misses + 1

    def test_originals_restored(self, tmp_path):
        """Exit puts back the original callables, also after an exception"""
        originals = {
            (module, name): getattr(module, name)
            for module in (core, tgis)
            for name in (
                "get_available_temporal_mapsets",
                "create_temporal_database",
                "init",
            )
        }
        with fakes.mapsets_cache():
            assert core.init is not originals[(core, "init")]
            assert tgis.init is core.init
        for (module, name), original in originals.items():
            assert getattr(module, name) is original
        with pytest.raises(RuntimeError, match=BOOM), fakes.mapsets_cache():
            raise RuntimeError(BOOM)
        for (module, name), original in originals.items():
            assert getattr(module, name) is original


class TestInterfaceCache:
    def test_answers_equal_real_io_through_changes(self, tmp_path):
        """Cached description and make_cmd() equal the real ones after changes"""
        with temporal_session(tmp_path / "a") as session:
            real = interface_state()
            assert "nprocs=3" not in real[1]
            with fakes.interface_cache() as stats:
                assert interface_state() == real
                assert interface_state() == real
                assert stats.hits == 1
                # NPROCS is in the GISRC; the default of nprocs follows it.
                gs.run_command("g.gisenv", set="NPROCS=3", env=session.env)
                changed = interface_state()
                assert "nprocs=3" in changed[1]
            assert interface_state() == changed
            with fakes.interface_cache():
                for name in ("r.mapcalc", "g.region", "t.info"):
                    first = interface_state(name)
                    assert interface_state(name) == first
        # Another project: other GISRC, so the answer of the first is not reused.
        with temporal_session(tmp_path / "b"):
            real = interface_state()
            assert "nprocs=3" not in real[1]
            with fakes.interface_cache() as stats:
                assert interface_state() == real
                assert interface_state() == real
                assert stats.hits == 1

    def test_key_without_gisrc_content_goes_stale(self, tmp_path):
        """A key of the tool name alone keeps the nprocs of the first session

        Negative test: shows that the comparison above sees this error.
        """
        with temporal_session(tmp_path / "a") as session:
            with fakes.interface_cache(key=lambda name: name):
                assert "nprocs=3" not in interface_state()[1]
                gs.run_command("g.gisenv", set="NPROCS=3", env=session.env)
                stale = interface_state()
            real = interface_state()
            assert "nprocs=3" in real[1]
            assert stale != real

    def test_other_commands_reach_the_real_popen(self, tmp_path):
        """Only the description is cached; running a module is not"""
        with temporal_session(tmp_path / "a"), fakes.interface_cache():
            module = Module("g.region", flags="p", run_=False)
            module.run()
            assert module.returncode == 0

    def test_originals_restored(self):
        """Exit puts back the original Popen, also after an exception"""
        original = pygrass_module.Popen
        with fakes.interface_cache():
            assert pygrass_module.Popen is not original
        assert pygrass_module.Popen is original
        with pytest.raises(RuntimeError, match=BOOM), fakes.interface_cache():
            raise RuntimeError(BOOM)
        assert pygrass_module.Popen is original
