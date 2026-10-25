"""Read space time datasets and single maps as series"""

from grass.exceptions import FatalError
from grass.temporal.state import get_current_mapset
from grass.temporal.factory import dataset_factory
from grass.temporal.open_stds import _parse_id, open_old_stds

from ._adapters import extent_of, space_of
from .content import MapRef
from .maptypes import KINDS_OF_STDS, MAP_CLASSES
from .series import Series, Slot


# Each map type has messages of its own rather than one message with the
# name of the type inserted, so that translators can inflect the whole
# sentence. The functions call _() when an error is raised, as for the other
# messages, and not once at import. "Raster map" is the wording of the
# former raster-only message, "Vector map" that of the classic vector
# algebra (temporal_vector_algebra.py) and "3D raster" that of the messages
# in space_time_datasets.py.
def _dataset_missing(stds_type):
    return {
        "strds": _("Space time raster dataset <{name}> not found"),
        "str3ds": _("Space time 3D raster dataset <{name}> not found"),
        "stvds": _("Space time vector dataset <{name}> not found"),
    }[stds_type]


def _map_missing(kind):
    return {
        "raster": _("Raster map <{name}> not found"),
        "raster3d": _("3D raster map <{name}> not found"),
        "vector": _("Vector map <{name}> not found"),
    }[kind]


def _map_unregistered(kind):
    return {
        "raster": _(
            "Raster map <{name}> has neither a registration in the temporal "
            "database nor a time stamp"
        ),
        "raster3d": _(
            "3D raster map <{name}> has neither a registration in the temporal "
            "database nor a time stamp"
        ),
        "vector": _(
            "Vector map <{name}> has neither a registration in the temporal "
            "database nor a time stamp"
        ),
    }[kind]


def _qualified(name):
    return name if "@" in name else f"{name}@{get_current_mapset()}"


def _slot_of(map_):
    return Slot(extent_of(map_), MapRef(map_.get_id()), space_of(map_), map_.get_id())


def source(name, *, where=None, stds_type="strds", order="time"):
    """The registered maps of a space time dataset as series

    Needs a GRASS session and a temporal database.

    :param name: the dataset, for "strds" optionally with a semantic label
        ("name.label[@mapset]"), which keeps only the maps with that label
    :param where: an SQL condition on the registered maps, as in t.rast.list
    :param stds_type: "strds", "str3ds" or "stvds"
    :param order: how the series sorts the maps, "time" (start, then end) or
        "start" (start only, see Series). With "start" maps of equal start
        stay in the order in which the temporal database lists them, as the
        classic algebra reads them, which the end time would override.
    :raises FatalError: if the dataset does not exist
    :raises ValueError: for another stds_type or order
    """
    if stds_type not in KINDS_OF_STDS:
        msg = f"stds_type must be one of {', '.join(KINDS_OF_STDS)}, got {stds_type!r}"
        raise ValueError(msg)
    ident = _qualified(name)
    # "name.label" of a raster dataset names the dataset without the label;
    # open_old_stds() below applies the label to the registered maps.
    base, mapset, _label = _parse_id(ident, stds_type)
    # open_old_stds() reports a missing dataset with msgr.fatal(), which
    # exits the process unless the messenger raises on errors, which
    # tgis.init(raise_fatal_error=True) sets up (core.py).
    if not dataset_factory(stds_type, f"{base}@{mapset}").is_in_db():
        raise FatalError(_dataset_missing(stds_type).format(name=ident))
    dataset = open_old_stds(ident, stds_type)
    maps = dataset.get_registered_maps_as_objects(where=where, order="start_time")
    return Series(
        tuple(_slot_of(map_) for map_ in maps or []),
        KINDS_OF_STDS[stds_type],
        order=order,
    )


def source_map(name, *, timestamp=True, kind="raster"):
    """A single map as series

    With timestamp, the map has its time stamp: the registered one if the map
    is in the temporal database, otherwise the one read from the GRASS
    database (r.timestamp), as the classic algebra does, so a single map
    stamped with r.timestamp is usable without registration. Without
    timestamp, the map has none and apply() uses it in every slot.

    :param kind: "raster", "raster3d" or "vector"
    :raises FatalError: if the map does not exist, or with timestamp if it has
        no time stamp at all
    :raises ValueError: for another kind
    """
    if kind not in MAP_CLASSES:
        msg = f"kind must be one of {', '.join(MAP_CLASSES)}, got {kind!r}"
        raise ValueError(msg)
    map_ = MAP_CLASSES[kind](_qualified(name))
    if not map_.map_exists():
        raise FatalError(_map_missing(kind).format(name=map_.get_id()))
    if not timestamp:
        map_.load()
        return Series((Slot(None, MapRef(map_.get_id()), space_of(map_)),), kind)
    if map_.is_in_db():
        map_.select()
    else:
        # Read the time stamp from the GRASS database, as the classic
        # _open_single_map() does, so a map stamped with r.timestamp but not
        # registered is usable.
        map_.load()
        map_.read_timestamp_from_grass()
        if map_.get_temporal_extent_as_tuple()[0] is None:
            raise FatalError(_map_unregistered(kind).format(name=map_.get_id()))
    return Series((_slot_of(map_),), kind)
