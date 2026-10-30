"""The image of the temporal database: what the library writes and reads back

``write_scenario`` runs every kind of write the library has in a session and
``normalized_dump`` turns the resulting database into SQL text that equals
between runs (times, user and register table names replaced by fixed values).
``read_cases`` lists what the library prints and returns when it reads that
image back, in the form that ``grass.temporal.testing.recordings`` records and
compares. The image is proof, not a test oracle: it holds what the code wrote
on the day it was recorded.

To record again (only with the permission of the maintainer, after a fix of a
bug that changes a result, never to make a refactor pass), run outside a
GRASS session with the GRASS tools in PATH::

    python3 -m grass.temporal.testing.database_image image <directory>

This writes ``database_write.sql`` and ``database_read.json.gz`` to the
directory. The module does not import pytest.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import re
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .data import MAP_TYPE_OF_STDS
from .recordings import record


def write_scenario(tools) -> None:
    """Write every kind of record the library writes to the temporal database

    Creates datasets of the three types in absolute and in relative time,
    registers maps through the tools and through the library (a raster map
    with a semantic label, a vector map with a second layer), updates the
    metadata, shifts, snaps, renames, copies, merges, unregisters and
    removes. The session must be a temporal_session(), because the library
    route runs in this process. What the scenario writes is the image that
    normalized_dump() turns into text.
    """
    saved_argv = sys.argv
    # The library stores the command line of the process in the command
    # history of a dataset it writes itself. The command line of pytest or
    # of the recording differs between runs, so the history gets a fixed one.
    sys.argv = ["scenario"]
    try:
        _write_scenario(tools)
    finally:
        sys.argv = saved_argv


def _write_scenario(tools) -> None:
    from grass.temporal.testing import data  # noqa: PLC0415

    data.small_region(tools, 1, 1, depths=1)
    spec = data.MapSpec
    day = data.day

    raster = [
        spec("img_1", 1, day(0), day(31), "S2_1"),
        spec("img_2", 2, day(31), day(59), "S2_1"),
        spec("img_3", 3, day(59), day(90), "S2_2"),
        spec("img_4", 4, day(100), day(120)),
    ]
    data.create_stds(tools, "strds", "abs_raster", raster, title="Absolute raster")
    data.create_stds(
        tools,
        "strds",
        "rel_raster",
        [spec(f"rel_{n}", n, n * 10, n * 10 + 10) for n in (1, 2, 3)],
        temporaltype="relative",
        unit="days",
        title="Relative raster",
    )
    data.create_stds(
        tools,
        "str3ds",
        "abs_raster3d",
        [spec(f"vol_{n}", n, day(n), day(n + 1)) for n in (1, 2, 3)],
        title="Absolute 3D raster",
    )
    data.create_stds(
        tools,
        "str3ds",
        "rel_raster3d",
        [spec(f"rvol_{n}", n, n, n + 2) for n in (1, 2)],
        temporaltype="relative",
        unit="years",
    )
    # A vector map with two layers is registered once per layer.
    data.vector_points(
        tools, "pts_a", [(0.5, 0.5), (0.2, 0.2)], attributes={"v": [1.0, 2.0]},
        layers=(1, 2),
    )  # fmt: skip
    data.make_map(tools, "vector", "pts_b", 2)
    data.make_map(tools, "vector", "pts_c", 3)
    data.make_map(tools, "vector", "pts_d", 4)
    data.make_map(tools, "vector", "pts_e", 5)
    data.register_stds(
        tools,
        "stvds",
        "abs_vector",
        [
            spec("pts_a", None, day(0), day(10)),
            spec("pts_a:2", None, day(0), day(10)),
            spec("pts_b", None, day(10)),
            spec("pts_c", None, day(20), day(30)),
        ],
    )
    data.register_stds(
        tools,
        "stvds",
        "rel_vector",
        [spec("pts_d", None, 1, 3), spec("pts_e", None, 3, 8)],
        temporaltype="relative",
        unit="months",
    )
    # The route through the library writes the same rows by other calls.
    for name in ("lib_1", "lib_2", "lib_3", "lib_4"):
        data.make_map(tools, "raster", name, 1)
    data.register_stds(
        tools,
        "strds",
        "lib_abs",
        [spec("lib_1", 1, day(0), day(5)), spec("lib_2", 2, day(5), day(9))],
        via="library",
    )
    data.register_stds(
        tools,
        "strds",
        "lib_rel",
        [spec("lib_3", 1, 0, 4), spec("lib_4", 2, 4, 9)],
        temporaltype="relative",
        unit="days",
        via="library",
    )

    # Metadata, title, description and semantic type; -m reads the maps again.
    tools.t_support(
        input="abs_raster", type="strds", title="Changed title",
        description="Changed description", semantictype="max", flags="m",
    )  # fmt: skip
    tools.t_support(input="abs_vector", type="stvds", flags="m")
    tools.t_support(input="abs_raster3d", type="str3ds", flags="m")
    tools.r_support(map="img_4", semantic_label="S2_3")
    tools.t_support(input="abs_raster", type="strds", flags="m")

    tools.t_shift(input="lib_abs", type="strds", granularity="2 days")
    tools.t_shift(input="abs_raster3d", type="str3ds", granularity="1 month")
    tools.t_shift(input="rel_raster", type="strds", granularity="5")
    tools.t_snap(input="abs_raster", type="strds")
    tools.t_snap(input="rel_raster", type="strds")
    tools.t_rename(input="lib_rel", output="renamed_rel", type="strds")
    tools.t_copy(input="abs_raster", output="copied", type="strds")
    tools.t_merge(input="abs_raster,lib_abs", output="merged", type="strds")

    with TemporaryDirectory() as directory:
        names = data.register_file(Path(directory) / "maps.txt", ["img_4"])
        tools.t_unregister(type="raster", input="abs_raster", file=names)
    tools.t_unregister(type="vector", input="abs_vector", maps="pts_b")
    data.create_stds(
        tools,
        "str3ds",
        "gone_raster3d",
        [spec("gone_1", 1, day(0), day(2))],
    )
    tools.t_remove(inputs="gone_raster3d", type="str3ds", flags="f")
    # -d removes the maps from the database too, so the dataset has maps of
    # its own.
    data.create_stds(
        tools,
        "strds",
        "doomed",
        [spec(f"dm_{n}", n, day(n), day(n + 1)) for n in (1, 2)],
    )
    tools.t_remove(inputs="doomed", type="strds", flags="df")


_REGISTER_TABLE = re.compile(
    r"\b(?:raster|raster3d|vector)_map_register_[0-9a-f]{32}(?![0-9a-f])"
)
_COMMAND_TIME = re.compile(r"# \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")
_TEMPORARY_DIRECTORY = re.compile(r"[^\s\"=]*/tmp[0-9a-z_]{8}/")
# A fixed moment that parses like a real one, so that the read image can
# print it.
_MOMENT = "2000-01-01 00:00:00"
_USER = "user"


def normalized_dump(path: Path) -> str:
    """Return the temporal database at path as SQL text that equals between runs

    The schema first, then one INSERT per row; tables and rows are sorted.
    Values that differ between runs are replaced: the creation and
    modification times (also the one in tgis_metadata) by a fixed moment, creator and modifier by a fixed
    name, the time stamps and temporary directories in the stored command
    history, and the 32 hex digits of a register table name by the digest of
    the id of the dataset that owns the table, so the text does not depend
    on the order in which datasets were made. The result loads into an
    empty SQLite database.

    :raises ValueError: for a register table that no dataset owns
    """
    connection = sqlite3.connect(path)
    try:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
                " AND name NOT LIKE 'sqlite_%'"
            )
        ]
        owners = {}
        for name in names:
            columns = [
                row[1] for row in connection.execute(f'PRAGMA table_info("{name}")')
            ]
            for column in columns:
                if column.endswith("_register") and name.endswith("_metadata"):
                    for ident, table in connection.execute(
                        f'SELECT id, "{column}" FROM "{name}"'
                    ):
                        owners[table] = hashlib.md5(  # noqa: S324
                            ident.encode(), usedforsecurity=False
                        ).hexdigest()

        def register_name(match):
            table = match.group(0)
            if table not in owners:
                msg = f"Register table {table} has no owner"
                raise ValueError(msg)
            return table[: -len("0" * 32)] + owners[table]

        def clean(text: str) -> str:
            text = _REGISTER_TABLE.sub(register_name, text)
            text = _COMMAND_TIME.sub("# TIME ", text)
            return _TEMPORARY_DIRECTORY.sub("TMPDIR/", text)

        lines = []
        for kind in ("table", "index", "view", "trigger"):
            statements = sorted(
                clean(row[0])
                for row in connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = ? AND sql IS NOT NULL"
                    " AND name NOT LIKE 'sqlite_%'",
                    (kind,),
                )
            )
            lines.extend(f"{statement};" for statement in statements)
        for name in sorted(names, key=clean):
            cursor = connection.execute(f'SELECT * FROM "{name}"')
            columns = [column[0] for column in cursor.description]
            rows = []
            for row in cursor:
                values = []
                for column, value in zip(columns, row, strict=True):
                    if column in {"creation_time", "modification_time"}:
                        value = _MOMENT if value is not None else None
                    elif (
                        name == "tgis_metadata"
                        and column == "value"
                        and row[0] == "creation_time"
                    ):
                        value = _MOMENT
                    elif column in {"creator", "modifier"}:
                        value = _USER if value is not None else None
                    elif isinstance(value, str):
                        value = clean(value)
                    values.append(
                        connection.execute("SELECT quote(?)", (value,)).fetchone()[0]
                    )
                rows.append(f'INSERT INTO "{clean(name)}" VALUES({",".join(values)});')
            lines.extend(sorted(rows))
    finally:
        connection.close()
    return "\n".join(lines) + "\n"


def load_image(text: str, path: Path) -> None:
    """Replace the SQLite database at path by the image in text"""
    Path(path).unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(text)
        connection.commit()
    finally:
        connection.close()


def _printed(function) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        function()
    return buffer.getvalue()


def _rows(value):
    """Rows of a query as tuples, a dictionary of them per mapset"""
    if isinstance(value, dict):
        return {key: _rows(rows) for key, rows in sorted(value.items())}
    return [tuple(row) for row in value]


_STDS_TYPES = ("strds", "str3ds", "stvds")
_TEMPORAL_TYPES = ("absolute", "relative")


def read_cases():
    """The cases of the read image: what the library reads from the image

    The temporal database of the session must hold the image that
    database_write.sql restores. Time stamps and the user were replaced
    there, so the result does not depend on when the image was recorded.
    """
    import grass.temporal as tgis  # noqa: PLC0415

    listing = []
    for temporal in _TEMPORAL_TYPES:
        for kind in (*_STDS_TYPES, *MAP_TYPE_OF_STDS.values()):
            for label, options in (
                ("all", {}),
                ("columns", {"columns": "id,name,creator"}),
                ("ordered", {"columns": "id", "order": "id DESC"}),
                ("where", {"columns": "id", "where": "name LIKE '%a%'"}),
            ):
                yield (
                    f"list/{kind}/{temporal}/{label}",
                    lambda kind=kind, temporal=temporal, options=options: _rows(
                        tgis.get_dataset_list(kind, temporal, **options)
                    ),
                )
            listing.append((kind, temporal))
    both = ["strds", "stvds"]
    yield "list/several", lambda: _rows(
        {k: [tuple(dict(r).items()) for r in v] for k, v in
         tgis.get_dataset_list(both, ["absolute", "relative"], columns="id").items()}
    )  # fmt: skip

    identifiers = {}
    for kind in (*_STDS_TYPES, *MAP_TYPE_OF_STDS.values()):
        found = set()
        for temporal in _TEMPORAL_TYPES:
            for rows in tgis.get_dataset_list(
                kind, temporal, columns="id", order="id"
            ).values():
                found.update(row["id"] for row in rows)
        identifiers[kind] = sorted(found)

    variants = (
        {},
        {"columns": "id"},
        {"columns": "id,start_time,end_time", "order": "start_time"},
        {"columns": "id,start_time", "where": "start_time > '2001-01-15'"},
        {"columns": "id", "order": "id DESC"},
        {"columns": "id,name,mapset", "where": "id LIKE '%1%'"},
        {"columns": "id,start_time", "where": "start_time > '2001-01-15';"},
    )
    for kind in _STDS_TYPES:
        for ident in identifiers[kind]:

            def stds(kind=kind, ident=ident):
                dataset = tgis.dataset_factory(kind, ident)
                dataset.select()
                return dataset

            yield (
                f"stds/{kind}/{ident}/info",
                lambda stds=stds: [
                    _printed(lambda: stds().print_info()),
                    _printed(lambda: stds().print_shell_info()),
                ],
            )
            for number, options in enumerate(variants):
                yield (
                    f"stds/{kind}/{ident}/maps/{number}",
                    lambda stds=stds, options=options: _rows(
                        stds().get_registered_maps(**options) or []
                    ),
                )
            yield (
                f"stds/{kind}/{ident}/lists",
                lambda stds=stds: [
                    stds().get_map_time(),
                    stds().count_gaps() if stds().is_time_absolute() else None,
                    stds().get_temporal_type(),
                ],
            )
    for kind in MAP_TYPE_OF_STDS.values():
        for ident in identifiers[kind]:

            def one(kind=kind, ident=ident):
                dataset = tgis.dataset_factory(kind, ident)
                dataset.select()
                return dataset

            yield (
                f"map/{kind}/{ident}",
                lambda one=one: [
                    _printed(lambda: one().print_info()),
                    _printed(lambda: one().print_shell_info()),
                    one().get_registered_stds(),
                ],
            )


def record_database_image(directory: Path) -> None:
    """Run the scenario in a project of its own and record both images

    Writes database_write.sql, then loads it into a second project and writes
    database_read.json.gz from there. Run it outside a GRASS session, with
    the GRASS tools in PATH.
    """
    import grass.temporal as tgis  # noqa: PLC0415
    from grass.temporal.testing.session import temporal_session  # noqa: PLC0415
    from grass.tools import Tools  # noqa: PLC0415

    directory = Path(directory)
    with TemporaryDirectory() as work:
        with temporal_session(Path(work) / "write") as session:
            tools = Tools(session=session, consistent_return_value=True)
            write_scenario(tools)
            text = normalized_dump(Path(tgis.get_tgis_database_string()))
        (directory / "database_write.sql").write_text(text, encoding="utf-8")
        with temporal_session(Path(work) / "read"):
            load_image(text, Path(tgis.get_tgis_database_string()))
            record("database_read", read_cases(), directory)


def main(argv: list[str]) -> int:
    """Record the image: ``image <directory>``"""
    if len(argv) != 2 or argv[0] != "image":
        print(__doc__)
        return 2
    record_database_image(Path(argv[1]))
    print("database image: recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
