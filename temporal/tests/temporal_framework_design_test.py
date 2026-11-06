# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check the code design document of the temporal framework against the code

The document (python/grass/docs/src/temporal_framework_design/, built into
python/grass/docs/src/Temporal-Framework-Code-Design.pdf) shows Python
examples, their output and UML figures of the classes. These tests keep it
true:

- each example runs in the North Carolina sample dataset and prints the
  output that the document shows;
- each example calls only what the public contract of grass.temporal lists;
- each class, member, base class and composition that a figure draws exists
  in the code;
- the checked-in PDF is built from the sources as they are now, and the
  text of its listings, as MuPDF copies it, is the example files and their
  output, character for character;
- the supplement of the 2017 publication stays as it was published.

The examples run like the manuals in a project whose PERMANENT is a link to
the dataset's (grass.temporal.testing.nc_dataset), so without the dataset
the tests that run them fail with a message that says where to get it.
"""

from __future__ import annotations

import dataclasses
import getpass
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
from grass.grassdb.create import create_mapset
from grass.temporal.testing.contract_trace import called_names, missing_from_contract
from grass.temporal.testing.manual_examples import (
    NormalizeContext,
    example_environment,
    normalize,
)
from grass.temporal.testing.nc_dataset import (
    differences,
    find_dataset,
    project_in_dataset,
    snapshot,
)

REPOSITORY = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY / "python/grass/docs/src/temporal_framework_design"
EXAMPLES = SOURCE / "examples"
FIGURES = SOURCE / "figures"
PDF = SOURCE.parent / "Temporal-Framework-Code-Design.pdf"
SUPPLEMENT_2017 = SOURCE.parent / "Temporal-Framework-API-Description.pdf"
# Passed explicitly: the default of missing_from_contract() searches from the
# working directory, which may lie in another checkout.
CONTRACT = REPOSITORY / "python/grass/temporal/tests/data/public_contract.json"

# sha256sum of the file as published with Gebbert and Pebesma (2017), taken
# on 2026-11-06 from the file checked in by dccfdc9ed8.
SUPPLEMENT_2017_SHA256 = (
    "32b2cb43276cefefcd9b6171257873c1726f8dc7fd78a26cc81870e9851fb518"
)

# The name of the project and of the mapset that the document tells the
# reader to run the examples in; both show in the output of the examples.
PROJECT = "nc_spm_08_grass7"
MAPSET = "temporal_design"

# Each example with the examples that must run before it in the same mapset,
# because it reads their datasets or files, and its command line arguments.
# The benchmark registers 1000 maps in the document; 50 show the same
# output form in a fraction of the time.
EXAMPLE_RUNS = {
    "register": ((), ()),
    "aggregate": (("register",), ()),
    "sample": (("register", "aggregate"), ()),
    "algebra": (("register",), ()),
    "map_lists": ((), ()),
    "tracks": ((), ()),
    "trajectories": (("tracks",), ()),
    "benchmark": ((), ("50",)),
}


# The classes that the figures draw, by the name a figure uses. A name that
# a figure draws but this table lacks fails the test, so a new figure says
# here which class it means.
FIGURE_CLASSES = {
    "AbsoluteTemporalExtent": "grass.temporal.temporal_extent.AbsoluteTemporalExtent",
    "AbsoluteTimeRow": "grass.temporal.temporal_extent.AbsoluteTimeRow",
    "AbstractDataset": "grass.temporal.abstract_dataset.AbstractDataset",
    "AbstractMapDataset": "grass.temporal.abstract_map_dataset.AbstractMapDataset",
    "AbstractSpaceTimeDataset": (
        "grass.temporal.abstract_space_time_dataset.AbstractSpaceTimeDataset"
    ),
    "BaseRow": "grass.temporal.base.BaseRow",
    "Call": "grass.temporal.algebra.content.Call",
    "Column": "grass.temporal.rows.Column",
    "Const": "grass.temporal.algebra.content.Const",
    "DictSQLSerializer": "grass.temporal.rows.DictSQLSerializer",
    "Extent": "grass.temporal.algebra.series.Extent",
    "Kind": "grass.temporal.kinds.Kind",
    "MapDataset": "grass.temporal.datasets.MapDataset",
    "MapRef": "grass.temporal.algebra.content.MapRef",
    "MetadataRow": "grass.temporal.metadata.MetadataRow",
    "_PlanarExtentMethods": "grass.temporal.space_time_datasets._PlanarExtentMethods",
    "ProcessChain": "grass.temporal.algebra.materialize.ProcessChain",
    "Profile": "grass.temporal.algebra.profile.Profile",
    "Raster3DDataset": "grass.temporal.space_time_datasets.Raster3DDataset",
    "Raster3DMetadata": "grass.temporal.metadata.Raster3DMetadata",
    "RasterDataset": "grass.temporal.space_time_datasets.RasterDataset",
    "RasterMetadata": "grass.temporal.metadata.RasterMetadata",
    "RegisterRow": "grass.temporal.base.RegisterRow",
    "Relation": "grass.temporal.algebra.relations.Relation",
    "RelativeTemporalExtent": "grass.temporal.temporal_extent.RelativeTemporalExtent",
    "RelativeTimeRow": "grass.temporal.temporal_extent.RelativeTimeRow",
    "Row": "grass.temporal.rows.Row",
    "SQLDatabaseInterface": "grass.temporal.rows.SQLDatabaseInterface",
    "STR3DSMetadata": "grass.temporal.metadata.STR3DSMetadata",
    "STRDSMetadata": "grass.temporal.metadata.STRDSMetadata",
    "STVDSMetadata": "grass.temporal.metadata.STVDSMetadata",
    "_SemanticLabelsMetadata": "grass.temporal.metadata._SemanticLabelsMetadata",
    "Series": "grass.temporal.algebra.series.Series",
    "SeriesAggregate": "grass.temporal.algebra.content.SeriesAggregate",
    "SeriesReduce": "grass.temporal.algebra.content.SeriesReduce",
    "Slot": "grass.temporal.algebra.series.Slot",
    "Space": "grass.temporal.algebra.series.Space",
    "_SpaceTimeMetadata": "grass.temporal.metadata._SpaceTimeMetadata",
    "SpaceTimeRaster3DDataset": (
        "grass.temporal.space_time_datasets.SpaceTimeRaster3DDataset"
    ),
    "SpaceTimeRasterDataset": (
        "grass.temporal.space_time_datasets.SpaceTimeRasterDataset"
    ),
    "SpaceTimeVectorDataset": (
        "grass.temporal.space_time_datasets.SpaceTimeVectorDataset"
    ),
    "SpatialExtent": "grass.temporal.spatial_extent.SpatialExtent",
    "SpatialExtentRow": "grass.temporal.spatial_extent.SpatialExtentRow",
    "SpatioTemporalTopologyBuilder": (
        "grass.temporal.topology.SpatioTemporalTopologyBuilder"
    ),
    "StdsDataset": "grass.temporal.datasets.StdsDataset",
    "StdsMapRegister": "grass.temporal.stds_map_register.StdsMapRegister",
    "TemporalExtent": "grass.temporal.temporal_extent.TemporalExtent",
    "TemporalRasterAlgebraParser": (
        "grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser"
    ),
    "TopologyLinks": "grass.temporal.topology.TopologyLinks",
    "VectorDataset": "grass.temporal.space_time_datasets.VectorDataset",
    "VectorMetadata": "grass.temporal.metadata.VectorMetadata",
    "_VolumeExtentMethods": "grass.temporal.space_time_datasets._VolumeExtentMethods",
    # Modules that a figure draws as a box of functions.
    "algebra": "grass.temporal.algebra",
}


def sample_objects():
    """One object of each class whose instance attributes a figure draws

    Compositions and instance attributes exist only on objects. The datasets
    build their rows without a database, so this needs no session. The rows
    and the algebra values are built the way the datasets and the core build
    them.
    """
    import grass.temporal as tgis
    from grass.temporal import algebra as ta
    from grass.temporal.kinds import KINDS

    samples = [
        tgis.RasterDataset("a@m"),
        tgis.Raster3DDataset("a@m"),
        tgis.VectorDataset("a@m"),
        tgis.SpaceTimeRasterDataset("a@m"),
        tgis.SpaceTimeRaster3DDataset("a@m"),
        tgis.SpaceTimeVectorDataset("a@m"),
    ]
    samples += [
        getattr(dataset, part)
        for dataset in samples[:]
        for part in (
            "base",
            "absolute_time",
            "relative_time",
            "spatial_extent",
            "metadata",
            "stds_register",
        )
        if hasattr(dataset, part)
    ]
    samples.append(KINDS["raster"])
    extent = ta.Extent(datetime(2020, 1, 1), datetime(2020, 1, 2))
    slot = ta.Slot(extent, ta.MapRef("a@m"), ta.Space(1, 0, 1, 0))
    samples += [ta.Series((slot,), "raster"), slot, extent]
    return samples


def latex_text(text):
    """The text of a LaTeX argument as Python names: \\_ is _"""
    return text.replace("\\_", "_").strip()


# The pgf-umlcd forms that parse_figure() reads, with their number of brace
# arguments after an optional [...]. pgf-umlcd has more (\\association,
# \\implement, interface and object, ...); a figure that uses one fails until
# parse_figure() learns it, so that nothing a figure draws escapes the check.
UML_ENVIRONMENTS = {"class": 2, "abstractclass": 2}
UML_MEMBERS = {"attribute", "operation"}
UML_LINKS = {"composition", "aggregation", "unidirectionalAssociation"}
# What a figure may use besides: TikZ and fonts, which draw no class, member
# or link. \\texttt must name Class.member(), see parse_figure().
DRAWING_MACROS = {"draw", "node", "foreach", "fontsize", "selectfont", "scriptsize"}
MACRO = re.compile(r"\\([A-Za-z]+)")
CLASS_MEMBER = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*(?:\\_[A-Za-z0-9_]*)*)\(\)"
)


def braced_arguments(text, position, count, where):
    """The count brace arguments at position, after an optional [...]

    Returns the arguments and the position after the last one. Raises
    ValueError where the text does not have them, so that a form this test
    does not know fails instead of being skipped.
    """
    if text.startswith("[", position):
        position = text.index("]", position) + 1
    arguments = []
    for _ in range(count):
        if not text.startswith("{", position):
            msg = f"{where}: expected {count} arguments in braces"
            raise ValueError(msg)
        depth = 0
        for end in range(position, len(text)):
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            if depth == 0:
                break
        arguments.append(text[position + 1 : end])
        position = end + 1
    return arguments, position


def plain_name(argument, where):
    """A name argument with \\_ and \\textit{} only; anything else is an error"""
    text = re.sub(r"\\textit\{([^{}]*)\}", r"\1", argument)
    if re.search(r"[{}]|\\(?!_)", text):
        msg = f"{where}: cannot read <{argument}>"
        raise ValueError(msg)
    return latex_text(text)


def loop_variables(text):
    """The macros that \\foreach and its options define in a figure"""
    names = set()
    for variables in re.findall(r"\\foreach\s+((?:\\[A-Za-z]+/?)+)", text):
        names |= set(re.findall(r"\\([A-Za-z]+)", variables))
    names |= set(re.findall(r"(?:count=|as\s+)\\([A-Za-z]+)", text))
    return names


def parse_figure(path):
    """The classes of a figure and what it draws for each

    Returns a dict from class name to a dict with "bases", "members" and
    "links", where a link is (kind, role, multiplicity, target) of a
    \\composition, \\aggregation or \\unidirectionalAssociation that starts
    at the class. Names in \\texttt{Class.member()} count as members of Class.
    Raises ValueError for a macro or environment that it does not read.
    """
    text = re.sub(r"(?<!\\)%.*", "", path.read_text())
    allowed = DRAWING_MACROS | loop_variables(text)
    classes = {}

    def entry_of(name):
        return classes.setdefault(name, {"bases": [], "members": [], "links": []})

    current = None
    position = 0
    while match := MACRO.search(text, position):
        macro, position = match.group(1), match.end()
        where = f"{path.name}, \\{macro} at {match.start()}"
        if macro in {"begin", "end"}:
            (environment,), position = braced_arguments(text, position, 1, where)
            if environment == "tikzpicture":
                continue
            if environment not in UML_ENVIRONMENTS:
                msg = f"{where}: environment {environment} is not read"
                raise ValueError(msg)
            if macro == "end":
                current = None
                continue
            (name, _place), position = braced_arguments(
                text, position, UML_ENVIRONMENTS[environment], where
            )
            current = entry_of(plain_name(name, where))
        elif macro == "inherit" or macro in UML_MEMBERS:
            if current is None:
                msg = f"{where}: outside a class"
                raise ValueError(msg)
            (argument,), position = braced_arguments(text, position, 1, where)
            if macro == "inherit":
                current["bases"].append(plain_name(argument, where))
                continue
            member = re.split(r"[\s:(]", argument.lstrip("+-# "), maxsplit=1)[0]
            member = plain_name(member, where)
            # "..." marks a shortened list of members.
            if member != "...":
                current["members"].append((macro, member))
        elif macro in UML_LINKS:
            arguments, position = braced_arguments(text, position, 4, where)
            source, role, multiplicity, target = (
                plain_name(argument, where) for argument in arguments
            )
            entry_of(source)["links"].append((macro, role, multiplicity, target))
        elif macro == "texttt":
            (argument,), position = braced_arguments(text, position, 1, where)
            named = CLASS_MEMBER.fullmatch(argument)
            if named is None:
                msg = f"{where}: <{argument}> is not Class.member()"
                raise ValueError(msg)
            entry_of(named.group(1))["members"].append(
                ("operation", latex_text(named.group(2)))
            )
        elif macro not in allowed:
            msg = f"{where}: macro \\{macro} is not read"
            raise ValueError(msg)
    return classes


def resolve(name):
    """The class or module that FIGURE_CLASSES names, imported"""
    qualified = FIGURE_CLASSES[name]
    try:
        return importlib.import_module(qualified)
    except ModuleNotFoundError:
        module, _, attribute = qualified.rpartition(".")
        return getattr(importlib.import_module(module), attribute)


def has_member(owner, name, samples):
    """Whether a class, module or one of its sample objects has the member"""
    if hasattr(owner, name):
        return True
    if not isinstance(owner, type):
        return False
    if dataclasses.is_dataclass(owner) and name in {
        field.name for field in dataclasses.fields(owner)
    }:
        return True
    if name in {column.name for column in getattr(owner, "columns", ())}:
        return True
    return any(
        isinstance(sample, owner) and hasattr(sample, name) for sample in samples
    )


def link_problems(owner, role, multiplicity, target, samples):
    """What is wrong with a link of a figure, an empty list if it holds"""
    objects = [sample for sample in samples if isinstance(sample, owner)]
    if not objects:
        return [f"no sample object of {owner.__name__} to check <{role}>"]
    problems = []
    for item in objects:
        if not hasattr(item, role):
            problems.append(f"{type(item).__name__} has no <{role}>")
            continue
        value = getattr(item, role)
        values = value if "*" in multiplicity else (value,)
        problems += [
            f"{type(item).__name__}.{role} holds a {type(part).__name__}, "
            f"not a {target.__name__}"
            for part in values
            if not isinstance(part, target)
        ]
    return problems


def figure_files():
    return sorted(FIGURES.glob("*.tex"))


@pytest.mark.parametrize("figure", figure_files(), ids=lambda path: path.stem)
def test_figure_names_exist(figure):
    """Every class, base, member and link of a figure exists in the code"""
    classes = parse_figure(figure)
    assert classes, f"{figure.name} draws no class and names no Class.member()"
    unknown = sorted(set(classes) - set(FIGURE_CLASSES))
    assert not unknown, f"{figure.name}: add {unknown} to FIGURE_CLASSES"
    samples = sample_objects()
    problems = []
    for name, entry in classes.items():
        owner = resolve(name)
        for base in entry["bases"]:
            if base not in FIGURE_CLASSES:
                problems.append(f"base {base} of {name} is not in FIGURE_CLASSES")
            elif not issubclass(owner, resolve(base)):
                problems.append(f"{name} does not inherit from {base}")
        problems += [
            f"{name} has no {kind} {member}"
            for kind, member in entry["members"]
            if not has_member(owner, member, samples)
        ]
        for _kind, role, multiplicity, target in entry["links"]:
            if target not in FIGURE_CLASSES:
                problems.append(f"target {target} of {name} is not in FIGURE_CLASSES")
                continue
            problems += [
                f"{name}: {problem}"
                for problem in link_problems(
                    owner, role, multiplicity, resolve(target), samples
                )
            ]
    assert problems == [], f"{figure.name}:\n" + "\n".join(problems)


def test_every_figure_class_is_drawn():
    """FIGURE_CLASSES has no entry that no figure draws any more"""
    drawn = set()
    for figure in figure_files():
        for name, entry in parse_figure(figure).items():
            drawn |= {name, *entry["bases"]}
            drawn |= {target for *_, target in entry["links"]}
    assert sorted(set(FIGURE_CLASSES) - drawn) == []


def test_every_example_is_run():
    """Each example file has an entry in EXAMPLE_RUNS and an output file"""
    found = {path.stem for path in EXAMPLES.glob("*.py")}
    assert found == set(EXAMPLE_RUNS)
    assert {path.stem for path in EXAMPLES.glob("*.txt")} == set(EXAMPLE_RUNS)


@pytest.fixture
def example_mapset(tmp_path):
    """A session in the mapset of the examples, in a project of the dataset

    Yields the session and a working directory. On leaving, the test fails if
    anything below the dataset's PERMANENT changed (nc_dataset.snapshot).
    """
    dataset = find_dataset()
    before = snapshot(dataset)
    project = project_in_dataset(dataset, tmp_path / "grassdata", PROJECT)
    create_mapset(project / MAPSET)
    work = tmp_path / "work"
    work.mkdir()
    try:
        with gs.setup.init(project / MAPSET, env=os.environ.copy()) as session:
            yield session, work
    finally:
        changed = differences(before, snapshot(dataset))
        assert changed == [], f"the examples changed {dataset}:\n" + "\n".join(changed)


def run_example(name, env, work, arguments=()):
    """Run examples/<name>.py as a reader would, return the completed process"""
    return subprocess.run(
        [sys.executable, str(EXAMPLES / f"{name}.py"), *arguments],
        env=env,
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
    )


def run_prerequisites(name, env, work):
    for before in EXAMPLE_RUNS[name][0]:
        result = run_example(before, env, work, EXAMPLE_RUNS[before][1])
        assert result.returncode == 0, (
            f"{before}.py, needed by {name}.py, failed:\n{result.stderr}"
        )


@pytest.mark.timeout(600)
@pytest.mark.parametrize("name", sorted(EXAMPLE_RUNS))
def test_example_runs_and_prints_the_shown_output(name, example_mapset, tmp_path):
    session, work = example_mapset
    env = example_environment(session.env)
    run_prerequisites(name, env, work)
    result = run_example(name, env, work, EXAMPLE_RUNS[name][1])
    assert result.returncode == 0, result.stderr
    context = NormalizeContext(str(tmp_path / "grassdata"), getpass.getuser())
    shown = (EXAMPLES / f"{name}.txt").read_text()
    assert normalize(result.stdout, context) == shown


@pytest.mark.timeout(600)
@pytest.mark.parametrize("name", sorted(EXAMPLE_RUNS))
def test_example_uses_only_the_contract(name, example_mapset):
    session, work = example_mapset
    env = example_environment(session.env)
    run_prerequisites(name, env, work)
    names = called_names(EXAMPLES / f"{name}.py", env=env, cwd=work)
    contract = json.loads(CONTRACT.read_text())
    assert missing_from_contract(names, contract=contract) == []


def build_residues(folder: Path) -> set[str]:
    """The paths that the digest leaves out: digest.tex and the Makefile's RESIDUES

    RESIDUES lists what pdflatex and bibtex leave behind, which is also what
    make clean removes; reading it from the Makefile keeps the two digests
    equal.
    """
    makefile = (folder / "Makefile").read_text().replace("\\\n", " ")
    found = re.findall(r"^RESIDUES\s*=(.*)$", makefile, re.MULTILINE)
    assert len(found) == 1, "the Makefile must set RESIDUES once"
    return {"digest.tex", *found[0].split()}


def source_digest(folder: Path) -> str:
    """The SHA-256 of the sources below folder, as the Makefile computes it

    Each file that build_residues() does not name contributes one line, in
    the order of the relative paths: the relative path, a NUL byte, the hex
    SHA-256 of its content and a newline. The digest is the hex SHA-256 of
    these lines.
    """
    residues = build_residues(folder)
    files = {
        path.relative_to(folder).as_posix(): path
        for path in folder.rglob("*")
        if path.is_file() and path.relative_to(folder).as_posix() not in residues
    }
    # Sorted as text, as sort(1) does in the C locale; Path objects sort by
    # their parts, which puts "a/b" before "a.b".
    lines = [
        f"{relative}\0{hashlib.sha256(files[relative].read_bytes()).hexdigest()}\n"
        for relative in sorted(files)
    ]
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def pdf_keywords(pdf: Path) -> str:
    """The /Keywords string of the PDF's info dictionary, read from its bytes

    design.tex sets \\pdfobjcompresslevel=0, so the info dictionary is a plain
    object and needs no PDF library.
    """
    found = re.findall(rb"/Keywords\s*\(([^)]*)\)", pdf.read_bytes())
    assert len(found) == 1, f"{pdf.name} has {len(found)} /Keywords entries"
    return found[0].decode("ascii")


def test_pdf_is_built_from_the_current_sources():
    assert pdf_keywords(PDF) == source_digest(SOURCE), (
        f"{PDF.name} is older than its sources: run make in {SOURCE}"
    )


def listing_lines(text):
    """The lines of a text without trailing blanks and without blank lines"""
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def pdf_pages():
    """The lines of each page of the PDF as MuPDF copies its text

    mutool draw -F txt writes the text that MuPDF and the viewers built on it
    copy, one line per line of the page and a form feed after each page. A
    line that holds only a number is the page number and is dropped.
    """
    text = subprocess.run(
        ["mutool", "draw", "-q", "-F", "txt", "-o", "-", str(PDF)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        [line for line in listing_lines(page) if not re.fullmatch(r"\d+", line)]
        for page in text.split("\f")
    ]


@pytest.mark.parametrize("suffix", [".py", ".txt"])
def test_listing_text_in_the_pdf_equals_the_example_file(suffix):
    """The text that MuPDF copies from each listing is its file

    design.tex makes every space of a listing a real space of the text layer,
    so the copied text keeps the indentation. pdftotext of poppler 24.02
    drops the spaces at the start of a line even then, with -raw and without
    (measured 2026-11-06 on listings with real spaces), so the PDF is read
    with mutool. Each line of an example (.py) or of its shown output (.txt)
    must come out of the PDF as it is, blank lines dropped on both sides.
    Where a listing crosses a page, it goes on on the next page, after what
    may stand at its top.
    """
    if shutil.which("mutool") is None:
        pytest.skip("mutool (mupdf-tools) is needed to read the PDF")
    pages = pdf_pages()
    missing = [
        path.name
        for path in sorted(EXAMPLES.glob(f"*{suffix}"))
        if not contains_listing(pages, listing_lines(path.read_text()))
    ]
    assert missing == [], f"listings that differ from their file: {missing}"


def contains_listing(pages, block):
    """Whether the pages hold block, see the test above"""
    return any(
        line == block[0] and continues(pages, page_number, start, block)
        for page_number, lines in enumerate(pages)
        for start, line in enumerate(lines)
    )


def continues(pages, page_number, start, block):
    """Whether the rest of block follows line start of a page"""
    page, position = page_number, start
    for wanted in block[1:]:
        position += 1
        if position < len(pages[page]):
            if pages[page][position] != wanted:
                return False
            continue
        # The listing crosses a page: it goes on on the next page, below the
        # figures or the running text that LaTeX may put at its top.
        page += 1
        if page == len(pages) or wanted not in pages[page]:
            return False
        position = pages[page].index(wanted)
    return True


def test_the_2017_supplement_is_unchanged():
    digest = hashlib.sha256(SUPPLEMENT_2017.read_bytes()).hexdigest()
    assert digest == SUPPLEMENT_2017_SHA256
