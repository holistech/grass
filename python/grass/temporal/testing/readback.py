"""Read registered maps and t.info output back so tests can compare them

The helpers run the list tools and t.info as subprocesses of the session that
`tools` is bound to, so they need neither an in-process grass.temporal nor a
mirrored os.environ.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from typing import NamedTuple

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
        # name, so the white space is normalized before the search.
        if "not found in temporal database" not in " ".join(str(error).split()):
            raise
        return None


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
