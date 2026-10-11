"""Read space time datasets and single maps as series"""

from grass.exceptions import FatalError
from grass.temporal.core import get_current_mapset
from grass.temporal.factory import dataset_factory
from grass.temporal.open_stds import open_old_stds
from grass.temporal.space_time_datasets import RasterDataset

from ._adapters import extent_of, space_of
from .content import MapRef
from .series import Series, Slot


def _qualified(name):
    return name if "@" in name else f"{name}@{get_current_mapset()}"


def _slot_of(map_):
    return Slot(extent_of(map_), MapRef(map_.get_id()), space_of(map_), map_.get_id())


def source(name, *, where=None, stds_type="strds"):
    """The registered maps of a space time dataset as series

    Needs a GRASS session and a temporal database.

    :param where: an SQL condition on the registered maps, as in t.rast.list
    :raises FatalError: if the dataset does not exist
    :raises NotImplementedError: for a stds_type other than "strds"
    """
    if stds_type != "strds":
        msg = f"Reading {stds_type} datasets is not supported yet"
        raise NotImplementedError(msg)
    ident = _qualified(name)
    # open_old_stds() reports a missing dataset with msgr.fatal(), which
    # exits the process unless the messenger raises on errors, which
    # tgis.init(raise_fatal_error=True) sets up (core.py).
    if not dataset_factory(stds_type, ident).is_in_db():
        raise FatalError(_("Space time dataset <{name}> not found").format(name=ident))
    dataset = open_old_stds(ident, stds_type)
    maps = dataset.get_registered_maps_as_objects(where=where, order="start_time")
    return Series(tuple(_slot_of(map_) for map_ in maps or []), "raster")


def source_map(name, *, timestamp=True):
    """A single raster map as series

    With timestamp, the map has its registered time stamp and must be
    registered in the temporal database. Without, it has none and apply()
    uses it in every slot.

    :raises FatalError: if the map does not exist, or with timestamp if it is
        not registered
    """
    map_ = RasterDataset(_qualified(name))
    if not map_.map_exists():
        raise FatalError(_("Raster map <{name}> not found").format(name=map_.get_id()))
    if not timestamp:
        map_.load()
        return Series((Slot(None, MapRef(map_.get_id()), space_of(map_)),), "raster")
    if not map_.is_in_db():
        raise FatalError(
            _("Raster map <{name}> is not registered in the temporal database").format(
                name=map_.get_id()
            )
        )
    map_.select()
    return Series((_slot_of(map_),), "raster")
