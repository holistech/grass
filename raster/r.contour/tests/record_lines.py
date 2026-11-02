"""Record the contour lines of r.contour on maps without null cells

The recording is the reference for tests that must show a change to the level
selection or to the line tracing leaves these maps alone. It is not a test and
pytest does not collect it (the name does not match ``*_test.py``).

Run it inside a GRASS session of an XY project and give the output file::

    grass --tmp-project XY --exec python3 \
        raster/r.contour/tests/record_lines.py \
        raster/r.contour/tests/data/lines_without_nulls.json

The file ``data/lines_without_nulls.json`` was recorded on commit 6ce54e289e
(2026-11-02), before any change to r.contour. For each case it holds the
r.contour arguments, the levels of the attribute table, the number of lines and
nodes from ``v.info -t``, and the vertices of every line from
``v.out.ascii format=standard``, rounded to 1e-9. The lines are sorted by level
and then by their vertices, so the order does not depend on how the tracer
visits the cells.

``assert_cases_as_recorded()`` runs the cases again in the current session and
compares them with the file; the tests call it.

The maps are made here: smooth, at most 20 by 20 cells, no null cells. Cases
whose result the planned changes alter on purpose (a negative minimum, limits
outside the values, a maxlevel off the step grid, null cells, regions with one
or two rows or columns) are left out.
"""

import json
import sys
from pathlib import Path

import pytest

import grass.script as gs

DECIMALS = 9

# name: (region rows, region columns, r.mapcalc expression)
MAPS = {
    # Plane, values from 2 to 16.
    "ramp": (8, 8, "float(row() + col())"),
    # Smooth hills, values from 5 to 15 (r.mapcalc takes degrees in sin and cos).
    "hill": (12, 12, "10 + 5 * sin(row() * 25.0) * cos(col() * 20.0)"),
    # One dome, values from 50 to 250.
    "dome": (20, 20, "250 - (row() - 10)^2 - (col() - 10)^2"),
    # Integer map of the same dome.
    "dome_int": (20, 20, "int(250 - (row() - 10)^2 - (col() - 10)^2)"),
}

# name: (map, r.contour arguments)
CASES = {
    "levels_ramp": ("ramp", {"levels": "5,8.5,12"}),
    "levels_hill": ("hill", {"levels": "7,10,13"}),
    "levels_dome": ("dome", {"levels": "60,100,150,200"}),
    "levels_dome_int": ("dome_int", {"levels": "60,100,150,200"}),
    "step_ramp": ("ramp", {"step": 2}),
    "step_hill": ("hill", {"step": 1.5}),
    "step_dome": ("dome", {"step": 25}),
    "step_dome_int": ("dome_int", {"step": 20}),
    "step_limits_hill": ("hill", {"step": 1, "minlevel": 8, "maxlevel": 12}),
    "step_limits_dome": ("dome", {"step": 20, "minlevel": 60, "maxlevel": 200}),
    "step_limits_ramp": ("ramp", {"step": 3, "minlevel": 4, "maxlevel": 13}),
    "cut_hill": ("hill", {"levels": "7,10,13", "cut": 8}),
    "cut_step_dome": ("dome", {"step": 25, "cut": 40}),
}


def read_levels():
    """Return the level of every category from the attribute table"""
    levels = {}
    for row in gs.read_command("v.db.select", map="lines", separator="|").splitlines()[
        1:
    ]:
        cat, level = row.split("|")
        levels[int(cat)] = round(float(level), DECIMALS)
    return levels


def read_lines(levels):
    """Return the lines of the map as dictionaries of level and vertices"""
    text = gs.read_command("v.out.ascii", input="lines", format="standard")
    lines = []
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        # The header block ends at the first "L" or "B" record.
        if not words or words[0] not in {"L", "B"}:
            continue
        nodes, categories = int(words[1]), int(words[2])
        vertices = []
        for _ in range(nodes):
            x, y = next(rows).split()[:2]
            vertices.append([round(float(x), DECIMALS), round(float(y), DECIMALS)])
        cats = [int(next(rows).split()[1]) for _ in range(categories)]
        lines.append({"level": levels[cats[0]], "vertices": vertices})
    return sorted(lines, key=lambda line: (line["level"], line["vertices"]))


def record_case(name, args):
    """Run r.contour and return the recording of its output"""
    gs.run_command("r.contour", input=name, output="lines", quiet=True, **args)
    info = gs.parse_command("v.info", map="lines", flags="t")
    levels = read_levels()
    return {
        "arguments": args,
        "levels": sorted(set(levels.values())),
        "number_of_lines": int(info["lines"]),
        "number_of_nodes": int(info["nodes"]),
        "lines": read_lines(levels),
    }


def make_map(name):
    """Set the region of the map and make it"""
    rows, columns, expression = MAPS[name]
    gs.run_command("g.region", n=rows, s=0, e=columns, w=0, res=1)
    gs.mapcalc(f"{name} = {expression}", overwrite=True)


def assert_cases_as_recorded():
    """Run every recorded case again and compare it with the recording

    The region and the maps of the current session are changed.
    """
    path = Path(__file__).parent / "data" / "lines_without_nulls.json"
    recording = json.loads(path.read_text(encoding="utf-8"))
    made = None
    for case, expected in recording.items():
        name = expected["map"]
        if name != made:
            make_map(name)
            made = name
        got = record_case(name, expected["arguments"])
        gs.run_command("g.remove", type="vector", name="lines", flags="f", quiet=True)
        assert got["levels"] == pytest.approx(expected["levels"], abs=1e-9), case
        assert got["number_of_lines"] == expected["number_of_lines"], case
        assert got["number_of_nodes"] == expected["number_of_nodes"], case
        assert len(got["lines"]) == len(expected["lines"]), case
        for line, want in zip(got["lines"], expected["lines"], strict=True):
            assert line["level"] == pytest.approx(want["level"], abs=1e-9), case
            assert len(line["vertices"]) == len(want["vertices"]), case
            for vertex, want_vertex in zip(
                line["vertices"], want["vertices"], strict=True
            ):
                assert vertex == pytest.approx(want_vertex, abs=1e-9), case


def main(path):
    """Record every case and write the JSON file"""
    recording = {}
    for name in MAPS:
        make_map(name)
        for case, (map_name, args) in CASES.items():
            if map_name == name:
                recording[case] = {"map": name}
                recording[case].update(record_case(name, args))
                gs.run_command(
                    "g.remove", type="vector", name="lines", flags="f", quiet=True
                )
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(recording, stream, indent=1, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
