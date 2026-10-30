"""Read registered maps and t.info output back so tests can compare them

The helpers run the list tools and t.info as subprocesses of the session that
`tools` is bound to, so they need neither an in-process grass.temporal nor a
mirrored os.environ.

``list_maps``, ``stds_info``, ``map_info`` and ``info_text`` read the
registered maps and the metadata of datasets and maps; ``cell_values`` reads a
raster back; ``inventory`` lists what a session holds; ``message`` normalizes
the messages of a call. ``time_text``, ``days_text`` and ``delta_row`` read
nothing back: they format expected values the way the list tools print them.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from typing import NamedTuple

import grass.script as gs
from grass.tools import ToolError

# Maps the dataset type to the list tool and whether it reports min and max;
# vector maps have no value range.
_LIST_TOOLS = {
    "strds": ("t_rast_list", True),
    "str3ds": ("t_rast3d_list", True),
    "stvds": ("t_vect_list", False),
}


class Row(NamedTuple):
    """A registered map of a dataset as the list tools report it

    Times stay text as the tools print them, for example
    "2001-01-01 00:00:00", because tests compare them in that form. A map
    without end time has end None, a map without value range (all null, or a
    vector) has min and max None.
    """

    name: str
    start: str
    end: str | None
    min: float | None
    max: float | None


def list_maps(tools, stds_type, name, *, where=None):
    """The registered maps of a dataset as Rows, in start time order

    `tools` is a grass.tools.Tools bound to a session, stds_type one of
    "strds", "str3ds" and "stvds". An empty dataset gives an empty list.
    """
    try:
        tool, has_range = _LIST_TOOLS[stds_type]
    except KeyError:
        msg = f"Unknown dataset type {stds_type!r}, expected one of {list(_LIST_TOOLS)}"
        raise ValueError(msg) from None
    columns = "name,start_time,end_time" + (",min,max" if has_range else "")
    options = {"input": name, "columns": columns, "order": "start_time"}
    if where is not None:
        options["where"] = where
    # format=json gives typed values and a real null for a missing end, which
    # the plain format prints as the text "None".
    result = getattr(tools, tool)(format="json", **options)
    return [
        Row(
            record["name"],
            record["start_time"],
            record["end_time"],
            record.get("min"),
            record.get("max"),
        )
        for record in result.json["data"]
    ]


def stds_info(tools, stds_type, name):
    """t.info -g of the dataset as a dict

    Values are converted by Result.keyval: int or float where the text is a
    number (number_of_maps is 3, not "3"), otherwise the text t.info prints,
    so quoted times keep their quotes and a dataset that never held a map
    reports "None" for most keys. The converted form is what the existing
    t.info assertions of the tool tests compare against.
    """
    return tools.t_info(type=stds_type, input=name, flags="g").keyval


def inventory(tools):
    """The maps of the current mapset and the space time datasets

    Returns the names that g.list type=all gives for the current mapset and,
    for strds, str3ds and stvds in this order, the ids that t.list gives for
    the mapsets of the search path. Tests compare it before and after a
    refused run to show that the run left no new map and no new dataset
    behind; maps registered in an existing dataset do not show here.
    """
    return (
        tools.g_list(type="all", mapset=".").stdout.split(),
        [
            tools.t_list(type=stds_type, columns="id").stdout.split()
            for stds_type in ("strds", "str3ds", "stvds")
        ],
    )


def map_info(tools, map_type, name):
    """t.info -g of a map as a dict, or None if the map is not in the database

    map_type is "raster", "raster_3d" or "vector"; a vector layer is named
    "map:layer". The map keeps its entry in the temporal database after a
    space time dataset forgets it, so None means that the map is no longer
    registered anywhere, which is what t.unregister without a dataset and
    t.remove -r do. Any other failure of t.info is raised.
    """
    try:
        return tools.t_info(type=map_type, input=name, flags="g").keyval
    except ToolError as error:
        # t.info says so for a map that was never registered or was
        # unregistered, in the text "not found in temporal database"; the
        # message is wrapped at a width that depends on the length of the
        # name, so message() normalizes the white space before the search.
        if "not found in temporal database" not in message(error):
            raise
        return None


def cell_values(tools, raster):
    """The cells of a raster map as a list of floats, row by row

    A null cell is None. Meant for maps of a few cells (see small_region()),
    where a test derives the value of every cell by hand. r.out.ascii writes
    16 decimal places of a DCELL map and 6 of an FCELL map, so the values of
    an FCELL map are rounded to six decimal places.
    """
    words = tools.r_out_ascii(input=raster, flags="h", null_value="N").stdout.split()
    return [None if word == "N" else float(word) for word in words]


def message(source):
    """The messages of a tool call as one line of text

    source is the result of a call (its stderr) or the ToolError it raised
    (its text, which holds the stderr). GRASS wraps messages at a width that
    depends on the length of the names in them, so a check that a text is
    present or absent compares with the white space normalized; an absence
    check on the raw text passes however the text is wrapped.
    """
    text = getattr(source, "stderr", None)
    if text is None:
        text = str(source)
    return " ".join(text.split())


def info_text(tools, **kwargs):
    """t.info -g as a dict of text, for tests of the printed form

    The values stay text (``"3"``, not 3, and ``"None"`` as printed), so a
    test can compare the form that t.info prints; use stds_info() or
    map_info() for values.
    """
    return gs.parse_key_val(tools.t_info(flags="g", **kwargs).text)


def time_text(moment):
    """Return a time as the list tools print it, "None" for no time"""
    return "None" if moment is None else moment.strftime("%Y-%m-%d %H:%M:%S")


def days_text(value):
    """Return a number of days as the list tools print it, "None" for none"""
    return "None" if value is None else f"{float(value)}"


def delta_row(name, start, end, first):
    """Return the row of delta, deltagaps and gran for a map or a gap

    The map is in the mapset PERMANENT; name is None for a gap. first is the
    start of the first row.
    """
    length = None if end is None else (end - start).days
    return [
        "None" if name is None else f"{name}@PERMANENT",
        "None" if name is None else name,
        "None" if name is None else "PERMANENT",
        time_text(start),
        time_text(end),
        days_text(length),
        days_text((start - first).days),
    ]
