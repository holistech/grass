# Testing

New code should come with tests, and a bug fix should come with a test which
fails without the fix; when the code being fixed has no tests at all, add a
test for its basic functionality as well, so it is clear the fix did not break
it.

GRASS has two testing frameworks. Use _pytest_ for everything new. Use the
older _grass.gunittest_ framework when the test needs the North Carolina
sample dataset, or when it needs data supplied as files. Neither is currently
possible with _pytest_ in general. The temporal framework is an exception: its
tests use _pytest_ with synthetic data, and the tests of its manuals and of its
code design document read the sample dataset through a helper module, see
[Tests of the temporal framework](#tests-of-the-temporal-framework) and
[Tests that need the North Carolina sample dataset](#tests-that-need-the-north-carolina-sample-dataset).

The two live side by side in the source tree: _pytest_ tests go into a
`tests` directory next to the code they test, _grass.gunittest_ tests into a
`testsuite` directory.

## Running tests

Running tests requires a built and installed GRASS with the `grass` command
available. Point Python at that installation first:

```bash
export PYTHONPATH="$(grass --config python_path):${PYTHONPATH}"
export LD_LIBRARY_PATH="$(grass --config path)/lib:${LD_LIBRARY_PATH}"
```

Then run the tests of the tool you are working on:

```bash
pytest raster/r.slope.aspect/tests/
```

Running `pytest` without a path from the top of the source tree collects the
`testsuite` directories as well, because the collection patterns in
`pyproject.toml` include them. Most _grass.gunittest_ tests need a GRASS
session and the sample dataset, so they fail when run this way. Exclude them
as the CI does:

```bash
pytest -k "not testsuite"
```

A _grass.gunittest_ test runs inside a GRASS session instead. Give it a
temporary mapset, which is created and removed for each run:

```bash
cd raster/r.slope.aspect/testsuite
grass --tmp-mapset ~/grassdata/nc_spm_08_grass7/ \
    --exec python test_r_slope_aspect.py
```

The test files are not executable, so `--exec` needs `python` in front of
the file name, and some of them load data files by relative path, so run them
from their own directory. The North Carolina sample dataset used above is
available from <https://grass.osgeo.org/sampledata/north_carolina/>.

## Writing pytest tests

### File placement and naming

Tests of a tool go next to it, in a `tests` directory, in a file named after
the tool with dots replaced by underscores, e.g.
`raster/r.slope.aspect/tests/r_slope_aspect_test.py`. When a tool needs more
than one file, add the feature or domain under test, e.g.
`r_slope_aspect_memory_test.py`. Tests of libraries and packages use the full
name of the unit the same way, e.g. `lib/gis/tests/lib_gis_env_test.py`.

Both `<name>_test.py` and `test_<name>.py` are collected, so either is fine;
`<name>_test.py` is the more common form in the source tree.

### Session fixture

Most tests need a GRASS session with a project and some data, so they set one
up in a fixture. Putting the fixture in a `conftest.py` file next to the tests
is not required, but it is common, because it keeps the setup separate from
the tests and lets several test files share it. This is the session fixture
used by the _r.slope.aspect_ tests, in
`raster/r.slope.aspect/tests/conftest.py`:

```python
import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def xy_dataset_session(tmp_path):
    """Active session in an XY project with a raster (scope: function)"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session) as tools,
    ):
        tools.g_region(s=0, n=5, w=0, e=6, res=1)
        tools.r_mapcalc(expression="rows_raster = row()")
        yield session
```

Always pass `env=os.environ.copy()` to `gs.setup.init()`, never call
`gs.setup.init(project)` on its own. Without it the session modifies the
global environment, and since all tests run in the same process, a later test
which copies `os.environ` inherits whatever earlier tests left behind.

Create an XY project, as above, unless the test is about coordinate
reference systems or needs real ground units; then pass `epsg` to
`gs.create_project()`.

Creating a project and its data for every test is fine when the data is small,
as above. When the data is large, plentiful, or expensive to compute, give the
session fixture module scope so the tests share it, and add a function-scoped
fixture using `TemporaryMapsetSession` from `grass.experimental`. Each test
then gets its own mapset in the shared project, which keeps the tests isolated
from each other. This suits most tool tests; tests of data management tools
often need something else. `raster/conftest.py` follows this pattern.

Fixtures in a `conftest.py` are available to all tests below it in the
directory tree, so a fixture useful to a whole group of tools can live higher
up. The `raster`, `vector`, and `scripts` directories each have one, and many
`tests` directories use those instead of defining their own. The source tree
has many more examples than this page can show.

### Test functions

A test asks the fixture for the session and runs tools against it:

```python
from grass.tools import Tools


def test_slope_of_constant_slope_raster(xy_dataset_session):
    """Slope of a raster with a constant slope is constant"""
    tools = Tools(session=xy_dataset_session)
    tools.r_slope_aspect(elevation="rows_raster", slope="slope")
    stats = tools.r_univar(map="slope", format="json")
    assert stats["min"] == 45
    assert stats["max"] == 45
```

A result gives access to the output in several ways: `text`, `stdout`,
`keyval` for `format="shell"`, and `json` for `format="json"`, which can also
be subscripted directly as above. See the `Tools` documentation for the rest.

### Test data

Where possible, generate small, deterministic data instead of using data
files. Raster algebra with _r.mapcalc_ covers most needs, using `row()` and
`col()` for predictable values, e.g. `elevation = 6 - col()`. Vector data can
come from _v.random_ with a fixed `seed`, or from _v.in.ascii_ and
_r.in.ascii_, which accept an `io.StringIO` object as their input parameter.
NumPy arrays can be passed to tools and requested back from them through
_grass.tools_.

When the test needs specific data which cannot be generated, the data has to
be supplied as files, which is currently possible only with _grass.gunittest_
in a `testsuite` directory. The tests of the temporal tools and of the library
do not need such data; the sample dataset is read only by the tests that run the
examples of the manuals and of the code design document, and by the test of the
helper that finds it; see
[Tests of the temporal framework](#tests-of-the-temporal-framework).

### Tests which run in parallel

Tests run in parallel, several per process, so a test which changes
`os.environ` can break unrelated tests running next to it. This applies to
rendering and to _grass.temporal_, which reads the session from the global
environment. Mark such a test so it is run on its own:

```python
@pytest.mark.needs_solo_run
def test_something_which_changes_the_environment(xy_dataset_session):
    ...
```

## Tests of the temporal framework

The helpers for tests of _grass.temporal_ and of the `t.*` tools are in the
package `grass.temporal.testing`. No module of it imports pytest when it is
imported (`postgresql` imports it inside `server_or_skip()` only), so it can
be used from any test; the shared fixtures that wrap it are in
`temporal/conftest.py` and in `python/grass/temporal/tests/conftest.py`, and
the test directories of the tools add their own in their `conftest.py`.

- `session`: `project_session()` and `temporal_session()` create a project
  and yield a session. `add_mapset()` adds a mapset to it, and
  `mapset_session()` opens a second session in another mapset of the same
  project, as the `two_mapsets` fixture of `temporal/conftest.py` does for
  tests of tools that cross mapsets. `run_with_timeout()` runs a tool in a
  process group of its own and kills the group when the tool does not end
  in time, for tests of tools that may hang.
- `data`: `create_stds()`, `register_stds()` and `make_map()` build
  datasets and maps from a few lines of description;
  `create_daily_stds()` makes the same maps of one day each and registers
  them in several datasets; `day()`, `timestamp()`,
  `intervals()` and `relative_intervals()` give the times. `vector_points()`
  makes a point map with an attribute table, in one or more layers;
  `register_file()` writes the input file of _t.register_ and
  _t.unregister_; `small_region()` sets a region of a few cells for tests
  that query values at coordinates. `create_timed_stds()` makes a dataset of
  constant maps from a list of (start, end) times.
- `readback`: `list_maps()` and `stds_info()` read the registered maps and
  the output of _t.info_ back as values that a test compares; `map_info()`
  does the same for a single map and gives `None` for one that is not in the
  temporal database. `cell_values()` reads the cells of a map of a few
  cells as a list, null as `None`. `message()` returns the
  messages of a call or of the error it raised as one line; compare messages
  through it, because GRASS wraps them and an absence check on the raw text
  passes whatever the text says. `info_text()` parses the output of
  `t.info -g` into a dictionary. `inventory()` lists the maps of the current
  mapset and the datasets of the search path, so that a test can show that a
  refused run left nothing behind; it needs a `Tools` object created with
  `consistent_return_value=True`, because otherwise a call that prints
  nothing, such as _t.list_ for a type without datasets, returns `None`.
  `time_text()`, `days_text()` and `delta_row()` format times, day counts
  and a row of the methods delta, deltagaps and gran the way the list tools
  print them.

The other modules of the package serve the comparisons of the algebras, the
recordings of the library and the cached IO described below; the docstring
of `grass.temporal.testing` lists them all.

Tests of the `t.*` tools and of _grass.temporal_ build all their data with these
helpers, in a project created in `tmp_path`, and do not read the North Carolina
dataset; only the tests of the manuals, the tests of the examples of the code
design document and the test of `nc_dataset` itself do, see
[Tests of the manuals](#tests-of-the-manuals-of-the-temporal-tools) and
[Tests of the developer
documentation](#tests-of-the-developer-documentation-of-the-temporal-framework).
Constant maps
from _r.mapcalc_ make the expected values derivable by hand: the comment
next to an expected value shows the arithmetic. A value that cannot be derived,
such as the file written by an export format, may be measured once; the
comment then names the date and the command, says why it cannot be derived, and
a derived check of its plausibility stands next to it. A tool's tests go into
`temporal/<tool>/tests/`, in files named like the tool with the dots replaced by
underscores and a topic, for example `temporal/t.shift/tests/t_shift_test.py`.
They run in parallel with _pytest-xdist_ like all other pytest tests, so a
module builds its datasets once in a module-scoped session and a test never
changes what another test reads; a test which changes `os.environ` is marked as
described above.

Which session to use depends on how the test reaches GRASS:

- A test which only runs tools, with `Tools(session=session)` or
  `env=session.env`, needs `project_session()`. The fixture
  `xy_module_session` provides it for a whole test module.
- A test which calls _grass.temporal_ in the test process needs
  `temporal_session()`, because the library reads the session from
  `os.environ`. It mirrors the session into `os.environ`, runs
  `tgis.init()` and makes errors raise instead of exiting. On exit it
  restores `os.environ`, the raise-on-error flag of the library and the
  error mode of the messenger; the database connection and mapset that
  `tgis.init()` binds stay bound until the next `init()`. The fixture
  `temporal_module_session` provides it. A new test of this kind
  carries `@pytest.mark.needs_solo_run`, as described above.

Each test module gets its own session, also when several directories run in
one pytest call. A `conftest.py` in a `tests` directory that defines a
fixture with the same name takes precedence over the shared one.

Tools which have both a classic and a core algebra run on the one chosen by
the environment variable `GRASS_TEMPORAL_ALGEBRA`; unset or empty means the
core, and a value other than `core` and `classic` is an error. The fixture
`algebra_setting` is parametrized over `core` and `classic` and returns the
name. It is not applied automatically; a directory which wants both
algebras writes an autouse fixture which requests it and sets the variable
in the session environment the tools use:

```python
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE


@pytest.fixture(autouse=True)
def algebra(xy_module_session, algebra_setting):
    xy_module_session.env[ALGEBRA_VARIABLE] = algebra_setting
    yield algebra_setting
    xy_module_session.env.pop(ALGEBRA_VARIABLE, None)
```

In a directory whose tools read `GRASS_TEMPORAL_ALGEBRA`, a test which selects
the algebra itself, for example by running both and comparing them, carries
`@pytest.mark.fixed_algebra`. The marker only labels the test; it does not
select anything. The test picks its algebra itself and so runs once whatever
`GRASS_TEMPORAL_ALGEBRA` says. A run that wants every test once, such as the
classic run, selects with `-m "not fixed_algebra"`.

### Comparing the classic profile with the reference implementation

`-c` and `GRASS_TEMPORAL_ALGEBRA=classic` compute on the classic profile of
the algebra core. The reference implementation, `grass.temporal.classic`, is
the implementation of the classic algebra that is older than the profile. It
stays in the repository for good, because publications refer to its results,
and the profile has to reproduce them completely. The reference has no switch
and no value of `GRASS_TEMPORAL_ALGEBRA`; the private helper
`grass.temporal.testing.reference` reaches it, whatever the variable and the
`classic` argument say. Its function `run_reference(kind, expression,
basename=..., **options)` computes an expression like the parse method of
the public parser classes, for the kinds `raster`, `raster3d`, `vector` and
`select`. Do not use it outside tests.

The tests that compare the outcome of the profile or the core with that of
the reference do not run it. The module `grass.temporal.testing.corpus` holds
what the reference computed for each such case of the test suite, and
`reference_outcome(kind, expression, **options)` returns the stored outcome.
With `GRASS_TEMPORAL_REFERENCE=live` the reference runs instead, and a case
fails where it no longer computes what the corpus holds;
`GRASS_TEMPORAL_REFERENCE=record` records the corpus again, as the module
docstring describes. The corpus key hangs on the node id of the test: a test
that is renamed or moved finds no entry and fails, and its old entries stay in
the corpus as orphans. Record the corpus again for a renamed test. To find
orphans, run the tests in both settings of the algebra with
`GRASS_TEMPORAL_CORPUS_TRACE_DIR` set to an empty directory; then
`python3 -m grass.temporal.testing.corpus_orphans <directory>` lists the
entries that no test read. Tests of the reference itself, tests that check it
against values derived by hand, and the comparisons of the planned chain and
of the error texts in `temporal_algebra_core_plan_options_io_test.py`, which
have no outcome to store, still run it. The algebra cases of the library
tests that came from the former gunittest files
(`grass_temporal_algebra_legacy_*_test.py`) take their datasets and checks
from `grass.temporal.testing.algebra_cases`.

The module `grass.temporal.testing.expressions` generates seeded random
expressions of the classic grammar, runs them with two of the runners of
`grass.temporal.testing.differential` (the reference, the classic profile
and the core) and compares the error class or the registered maps, with
their time stamps and values. The same seed gives the same expression, so a
difference can be reproduced from its seed alone. The test modules
`*_fuzz_test.py` of the four tools run the seeds 0 to 199 per kind in the
normal run; they carry the marker `slow`, which `-m "not slow"` deselects, and
`fixed_algebra`. Two variables widen a run for an acceptance; with either of
them set, the tests compute on the reference instead of reading the corpus:

```bash
GRASS_TEMPORAL_FUZZ_COUNT=4000 GRASS_TEMPORAL_FUZZ_SEED=0 \
    pytest temporal/t.rast.algebra/tests/t_rast_algebra_fuzz_test.py
```

Outside pytest, the module writes one JSON line per expression, so that a
run before and after a change can be compared:

```bash
python3 -m grass.temporal.testing.expressions --kind raster \
    --seeds 0-3999 --runner reference --out before.jsonl
# change the code, run the same command with --out after.jsonl, then:
python3 -m grass.temporal.testing.expressions --diff before.jsonl after.jsonl
```

An expression on which the reference and the classic profile differ is an
error of the profile, unless it is a documented difference: message texts,
debug output, the class of the error of an invalid expression (the profile
reads the whole expression first and reports the syntax error), and a
relation over a list of absolute and relative time (the reference stops with a
`TypeError`). The section "Differences from the reference implementation" of
the _t.rast.algebra_ manual describes them; two more, the time of a partner
whose box only touches and the `CalledModuleError` of a failed module, are
items 16 and 17 of its corrections. The module docstring lists the options.

### Recordings of the library

Two modules record what the library computes and compare a later run with the
record, so that a refactor which changes a result shows with the name of the
case. `grass.temporal.testing.recordings` covers the extent, granularity, date
and topology functions on fixed grids of inputs, and
`grass.temporal.testing.database_image` the temporal database that the library
writes and what it reads back from it. The records are in
`python/grass/temporal/tests/recordings`, and
`grass_temporal_recordings_test.py` and `grass_temporal_database_image_test.py`
compare them with the current code. A record is proof, not a test oracle: it
holds what the code computed on the day it was recorded, surprising results
included. Record again only with the permission of the maintainer, after a fix
that changes a result on purpose, never to make a refactor pass; the module
docstrings give the commands.

### Tests against PostgreSQL

The temporal database is SQLite by default. Tests marked
`@pytest.mark.postgresql` and the fixture `postgresql_database` run against a
PostgreSQL server instead, which the tests do not start. Without the server
they are skipped, so an ordinary run is unchanged. Start a server bound to the
local interface only, name it in the environment, and remove it afterwards:

```bash
docker run -d --rm --name grass-tgis-pg -e POSTGRES_HOST_AUTH_METHOD=trust \
    -p 127.0.0.1:55432:5432 postgres:16
export GRASS_TEMPORAL_TEST_POSTGRESQL="host=127.0.0.1 port=55432 user=postgres dbname=postgres"
pytest -m postgresql -n auto python/grass/temporal/tests temporal/t.upgrade/tests
docker rm -f grass-tgis-pg
```

The tests need the Python package psycopg2 (without it they are skipped) and a
server of PostgreSQL 13 or newer, because dropping a database uses `DROP
DATABASE ... WITH (FORCE)`. The variable holds a libpq connection string of a
database from which the user may create others. The fixture creates a database
of its own for each test and drops it afterwards, so tests running in parallel
under `-n auto` never share one. The module `grass.temporal.testing.postgresql`
also has `rows_of()`, which reads a temporal database of either backend into the
same form, and `run_scenario()`, which fills one through the tools; together
they compare the two backends row by row. The tests are skipped, not reported as
an error, when the variable is unset or the server does not answer.

### Real and cached IO in library tests

Tests of the library mock the slow IO that always gives the same answer, where
a comparison with real IO shows that the mock is faithful. Tests of the IO
itself and tests of the tools (end to end) run with real IO. Comparisons of two
implementations run with real raster and database IO; they still get the
cached mapset list and tool descriptions, which both sides receive alike.

Two such caches exist, in `grass.temporal.testing.io_cache`. The directories
`python/grass/temporal/tests` and `temporal/t.*.algebra/tests` apply them to
every test through an autouse fixture in their `conftest.py`. Fixtures of
module scope are set up before that fixture and therefore use the real IO:

- the list of mapsets with a temporal database, which
  `grass.temporal.db.get_available_temporal_mapsets` otherwise asks
  _t.connect_ for each time a database connection is opened;
- the `--interface-description` of a tool, which pygrass otherwise reads by
  starting the tool each time a `Module` is created.

Both keys contain the content of the `GISRC` file, because the current mapset,
the search path and options such as `NPROCS` are stored there. The test
`grass_temporal_testing_fakes_test.py` compares each cached answer with the real
one across another project, a changed search path, a changed `NPROCS` and a
database created by a subprocess, and shows with weaker keys that the comparison
would see a stale answer. A test, or a whole module, that checks the search
path, the discovery of databases or the start of a session carries
`@pytest.mark.real_io`, which switches the caches off. Use it for every test
whose subject is the IO that is cached. A tool started as a subprocess never
sees the caches, because they live in the test process; the marker matters only
for the in-process part of such a test.

### Tests of the manuals of the temporal tools

The manual of each `t.*` tool and the introduction `temporal/temporalintro.md`
keep their examples under `## EXAMPLES`, and `temporal/tests` runs them:
what a reader copies from a manual has to work and has to print what the
manual shows. Four modules of `grass.temporal.testing` and one script do the
work.

- `manual_examples` reads a manual. Each `###` heading under `## EXAMPLES` is
  one example with two tabs, `=== "Command line"` (code blocks in `sh`) and
  `=== "Python (grass.tools)"` (blocks in `python`), as in
  `raster/r.sim/r.sim.water/r.sim.water.md`. A block of the language `text`
  right after a code block is the output that the manual shows for it. An HTML
  comment before a block, `<!-- example: key=value -->`, steers the test and
  stays invisible to the reader: `not-run` with a `reason`, or `requires=` one
  of `postgresql`, `old-database` and `gdal:<driver>`, which skip the block
  where the requirement is missing. The comment `<!-- example-project: ... -->`
  under `## EXAMPLES` says where the examples run. A catalog of expressions,
  such as the one of _t.rast.algebra_, has the `Command line` tab only and
  says so with `<!-- example: shell-only -->`. `run_manual` runs the blocks of
  a tab in a fresh session, one tab per test, and `check_manual` compares the
  output after `normalize()`, which replaces what differs from run to run:
  the database path, the user name in the creator fields, the creation and
  modification times, and the hexadecimal part of the name of a register
  table. A block that runs longer than `BLOCK_SECONDS` is stopped.
- `manual_coverage` checks that the examples of a manual show every option of
  the tool (`NOT_SHOWN` lists the options left out on purpose, and is empty
  today) and, with `check_html_sync`, that the `.md` and the `.html` file next
  to it agree.
- `nc_dataset` finds the North Carolina sample dataset, see the next section.
- `versions` turns a current temporal database into one of an older version,
  for the examples of _t.upgrade_ (`requires=old-database`) and the tests of
  the version check.
- `utils/grass_md2html.py` writes the `.html` file of a manual from its `.md`
  file. Edit only the `.md` file, then run
  `python3 utils/grass_md2html.py temporal/<tool>/<tool>.md`; with `--check`
  it writes nothing and exits with 1 when an `.html` file differs from the
  generated text. It refuses Markdown outside the subset that the manuals use,
  and an indentation under a list item that Python-Markdown (MkDocs) reads
  differently from CommonMark. `temporal/tests/temporal_manual_html_test.py`
  runs the same comparison for each manual.

A manual joins the test by an entry in `REVIEWED_MANUALS` in
`temporal/tests/temporal_manual_examples_test.py`; a manual that may keep a
catalog is also in `CATALOG_MANUALS`.

### Tests of the developer documentation of the temporal framework

Two modules in `temporal/tests` keep the developer documentation true; neither
checks prose, both check what the text claims about the code.

- `temporal_framework_page_test.py` checks the overview page
  `python/grass/docs/src/temporal_framework.rst`. Each Python code block runs
  in a new project and must end without a traceback; each block may call only
  what the public contract lists; every module and package of the library has
  a `:mod:` role on the page and every role names a module that exists. On this
  page only `.. code-block:: python` is read as a code block. The test
  rejects, instead of skipping, the directives `code`, `sourcecode`,
  `literalinclude`, `doctest` and `testcode`, any other `code-block`
  language, a line that ends in `::` (a literal block, also a lone `::`) and a
  line that starts with `>>>`; write Python examples as
  `.. code-block:: python`.

  The guides that join the overview page, listed in `PAGES` of that test, are
  read with more forms. A `code-block` with a `:name:` of the form
  `example-<kind>-<what>` is part of an example that the test assembles in a new
  project: `example-tool-file` is the Python file of a tool or a script, written
  under its `:caption:`, `example-data-<what>` a text file,
  `example-commands-<what>` a block of commands, one per line (`python3` stands
  for the interpreter of the test), and `example-output-<what>` right behind it
  the standard output that those commands print. The test runs the commands,
  compares the output with the page and traces the tool against the contract,
  with the arguments of each call (`called_names(..., argv=...)`). A
  `literalinclude` must select a function (`:pyobject:`) or the lines after
  `:start-after:` and/or before `:end-before:` of a file that exists, each
  marker once; `:lines:` and the other line-number options are refused
  because they drift when the file changes. Every guide must appear in a
  toctree of the overview page, every role of a guide must name something that
  exists, and every function of `tool_steps` must be named on the tool guide;
  on the algebra guide, every dotted name of `grass.temporal.algebra` written
  as a literal must exist as well. No two blocks of the pages may share a
  `:name:`, because Sphinx makes each a label of the whole documentation. An
  unnamed Python block on a guide that does not run its snippets is refused, so
  that no code goes unrun.
- `temporal_framework_design_test.py` checks the code design document in
  `python/grass/docs/src/temporal_framework_design/`. Its examples run in the
  sample dataset and must print what the document shows; each class, member,
  base class and composition of a UML figure must exist in the code; the text of
  each listing in the PDF must equal the example file and its output.
  The test of the listings reads the PDF with `mutool` (MuPDF, package
  `mupdf-tools`); without it that test is skipped. Each example file must also
  be attached to the PDF under its name, byte for byte, which the test reads
  from the PDF in Python alone.

The checked-in PDF, `python/grass/docs/src/Temporal-Framework-Code-Design.pdf`,
carries the SHA-256 of its sources in its keywords, and the test compares it
with the digest of the sources as they are. A change of any source file, an
example, a figure or the text, therefore turns the test red until the PDF is
built again: run `make` in `python/grass/docs/src/temporal_framework_design/`
and commit the PDF together with `digest.tex`. The build needs LaTeX
(`pdflatex` and `bibtex`).

The examples of both documents may call only what the public contract lists
(`python/grass/temporal/tests/data/public_contract.json`); a name that only an
example of the documentation uses is entered with the origin `docs`.
`grass.temporal.testing.contract_trace` finds out what a script calls: it runs
the script and records, with `sys.setprofile`, the functions and methods of
`grass.temporal` that the script itself calls. The trace is a floor, not a
proof. A plain attribute read or a constant leaves no function name, and the
trace leaves out every name with a component that starts with an underscore:
constructors, `__repr__` and the container protocol methods (`__len__`,
`__iter__`). It does see operators (`a / b`, `a < b`) under the class that
defines the operator method, if that class is public, and a method that a
private base class defines under the public class of the object it was called
on. It traces only the main thread. Read an example as well as tracing it.

## Tests that need the North Carolina sample dataset

The tests of the manuals and the tests that run the examples of the code design
document (both in `temporal/tests`) run their examples on the North Carolina
sample dataset, through `grass.temporal.testing.nc_dataset`; so does the test of
that module in `python/grass/temporal/tests`. The test of the overview page
(`temporal_framework_page_test.py`) does not: it creates its own datasets in a
project in `tmp_path`. These tests look for it in the
folder named by the environment variable `GRASS_TEMPORAL_TEST_NC_SPM`; without
the variable they take `~/grassdata/nc_spm_08_grass7` and then
`~/grassdata/nc_spm_full_v2beta1`. When none is found, the tests fail with a
message instead of being skipped. Download the dataset from
<https://grass.osgeo.org/sampledata/north_carolina/nc_spm_08_grass7.zip>. The
tests only read it: they work in a temporary project and fail if the dataset
changes.

## More information

- [grass.gunittest documentation](https://grass.osgeo.org/grass-devel/manuals/libpython/gunittest_testing.html)
  for writing and running _grass.gunittest_ tests
- [testsuite/README.md](https://github.com/OSGeo/grass/blob/main/testsuite/README.md)
  for the root testsuite directory and continuous integration
- [pytest documentation](https://docs.pytest.org/) for fixtures,
  `parametrize`, and `pytest.raises`
- [AGENTS.md](https://github.com/OSGeo/grass/blob/main/AGENTS.md) for
  additional instructions for AI assistants and agents
