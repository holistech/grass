"""Test t.register under other locales, with a non-ASCII description

The former gunittest set the locale of the process to fr_BE.UTF-8 to catch a
UnicodeDecodeError. That locale is not installed everywhere, and a locale that
is missing falls back to the C locale, so the module runs the same steps with
C, C.UTF-8 and fr_BE.UTF-8 in the environment of the tools and skips a locale
that the system does not have. With LC_ALL empty, Python coerces the C locale
to UTF-8 (PEP 538), so "C" decodes the description as UTF-8 too.
"""

import pytest

from grass.exceptions import CalledModuleError
from grass.temporal.testing.data import make_map
from grass.temporal.testing.readback import list_maps, stds_info
from grass.temporal.testing.session import project_session
from grass.tools import Tools

# Almost every test of the module runs longer than one second (measured
# 18.10.2026 with pytest --durations).
pytestmark = pytest.mark.slow

LOCALES = ["C", "C.UTF-8", "fr_BE.UTF-8"]
DESCRIPTION = "Précipitation totale mensuelle NC"


@pytest.fixture(params=LOCALES)
def locale_tools(request, tmp_path):
    with project_session(tmp_path / "project") as session:
        # As the former test did: LC_ALL empty, so that Python may coerce
        # the C locale to UTF-8 (PEP 538), which it does not when LC_ALL is set.
        for key in ("LANG", "LC_CTYPE", "LC_TIME", "LC_MESSAGES"):
            session.env[key] = request.param
        session.env["LC_ALL"] = ""
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        try:
            tools.run_cmd(
                [
                    "python3",
                    "-c",
                    "import locale; locale.setlocale(locale.LC_ALL, '')",
                ]
            )
        except CalledModuleError:
            pytest.skip(f"locale {request.param} is not installed")
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        yield tools


def test_register_with_a_non_ascii_description(locale_tools):
    tools = locale_tools
    maps = []
    for number in (1, 2, 3):
        make_map(tools, "raster", f"prec_{number}", number)
        maps.append(f"prec_{number}")
    tools.t_create(
        output="pluies",
        semantictype="sum",
        title="precipitation_mois",
        description=DESCRIPTION,
    )

    tools.t_register(
        type="raster",
        input="pluies",
        maps=",".join(maps),
        start="2000-01-01",
        increment="1 months",
        flags="i",
    )

    rows = list_maps(tools, "strds", "pluies")
    assert [(row.name, row.start, row.end) for row in rows] == [
        ("prec_1", "2000-01-01 00:00:00", "2000-02-01 00:00:00"),
        ("prec_2", "2000-02-01 00:00:00", "2000-03-01 00:00:00"),
        ("prec_3", "2000-03-01 00:00:00", "2000-04-01 00:00:00"),
    ]
    info = stds_info(tools, "strds", "pluies")
    assert (info["number_of_maps"], info["granularity"]) == (3, "'1 month'")
    assert (
        DESCRIPTION.encode()
        in tools.t_info(type="strds", input="pluies").stdout.encode()
    )


def test_a_non_ascii_description_works_with_lc_all_c(tmp_path):
    # With LC_ALL set, Python does not coerce the locale (PEP 538) but still
    # runs in its UTF-8 mode (PEP 540), which grass.script's parser follows.
    with project_session(tmp_path / "project") as session:
        session.env["LC_ALL"] = "C"
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )

        tools.t_create(output="pluies", title="t", description=DESCRIPTION)

        assert DESCRIPTION in tools.t_info(type="strds", input="pluies").stdout
