"""The temporal framework of GRASS

The package exports the names that code outside the library uses, listed in
``__all__``. Everything else is imported from its module, for example
``from grass.temporal.db import DBConnection``.
"""

from grass.exceptions import FatalError

from . import core, datetime_math, list_stds, space_time_datasets
from .abstract_space_time_dataset import AbstractSpaceTimeDataset
from .aggregation import aggregate_raster_maps, collect_map_names
from .db import SQLDatabaseInterfaceConnection, SQLStatementError, init_dbif
from .schema import (
    get_sql_template_path,
    get_tgis_db_version_from_metadata,
    get_tgis_metadata,
    upgrade_temporal_database,
)
from .state import (
    get_current_mapset,
    get_tgis_c_library_interface,
    get_tgis_database_string,
    get_tgis_message_interface,
    init,
    profile_function,
    stop_subprocesses,
)
from .datetime_math import (
    adjust_datetime_to_granularity,
    check_suffix,
    create_numeric_suffix,
    datetime_after_steps,
    datetime_to_grass_datetime_string,
    increment_datetime_by_string,
    map_name_suffix,
    next_cycle,
    option_to_datetime,
    string_to_datetime,
    time_delta_to_relative_time,
)
from .extract import extract_dataset
from .factory import dataset_factory
from .gui_support import registered_maps_grouped, tlist, tlist_grouped
from .list_stds import get_dataset_list, list_maps_of_stds
from .mapcalc import dataset_mapcalculator
from .open_stds import (
    check_new_map_dataset,
    check_new_stds,
    open_new_map_dataset,
    open_new_stds,
    open_old_stds,
)
from .register import register_map_object_list, register_maps_in_space_time_dataset
from .sampling import sample_stds_by_stds_topology
from .space_time_datasets import (
    Raster3DDataset,
    RasterDataset,
    SpaceTimeRaster3DDataset,
    SpaceTimeRasterDataset,
    SpaceTimeVectorDataset,
    VectorDataset,
)
from .topology import SpatioTemporalTopologyBuilder
from .stds_export import export_stds
from .stds_import import import_stds
from .temporal_extent import AbsoluteTemporalExtent, RelativeTemporalExtent
from .temporal_granularity import (
    check_granularity_string,
    compute_absolute_time_granularity,
    compute_relative_time_granularity,
    gran_singular_unit,
    gran_to_gran,
)
from .univar_statistics import (
    print_gridded_dataset_univar_statistics,
    print_vector_dataset_univar_statistics,
)

# The algebra tools and tests of the package still run on the old temporal
# algebra. The three parsers come from the algebra core once it carries the
# algebra tools; the other names go with the tools and tests that use them.
from .temporal_algebra import TemporalAlgebraParser
from .temporal_raster3d_algebra import TemporalRaster3DAlgebraParser
from .temporal_raster_algebra import TemporalRasterAlgebraParser
from .temporal_raster_base_algebra import TemporalRasterAlgebraLexer
from .temporal_vector_algebra import TemporalVectorAlgebraParser

# Names the package exported before and tools still take from it: t.copy
# (AbstractMapDataset), t.rast.aggregate and t.rast.aggregate.ds
# (aggregate_by_topology), and six raster tools that build map name suffixes.
# They leave the package with the revision of those tools.
from .abstract_map_dataset import AbstractMapDataset
from .aggregation import aggregate_by_topology
from .datetime_math import create_suffix_from_datetime, create_time_suffix
from .state import STATE as _STATE


# The package offered these two getters before the database layer replaced
# core; they stay importable until the package gets its final list of names.
def get_tgis_backend():
    """Return the name of the database backend of the session"""
    return _STATE.backend


def get_tgis_database():
    """Return the database connection string of the session"""
    return _STATE.database_string


__all__ = [
    "AbsoluteTemporalExtent",
    "AbstractMapDataset",
    "AbstractSpaceTimeDataset",
    "FatalError",
    "Raster3DDataset",
    "RasterDataset",
    "RelativeTemporalExtent",
    "SQLDatabaseInterfaceConnection",
    "SQLStatementError",
    "SpaceTimeRaster3DDataset",
    "SpaceTimeRasterDataset",
    "SpaceTimeVectorDataset",
    "SpatioTemporalTopologyBuilder",
    "TemporalAlgebraParser",
    "TemporalRaster3DAlgebraParser",
    "TemporalRasterAlgebraLexer",
    "TemporalRasterAlgebraParser",
    "TemporalVectorAlgebraParser",
    "VectorDataset",
    "adjust_datetime_to_granularity",
    "aggregate_by_topology",
    "aggregate_raster_maps",
    "check_granularity_string",
    "check_new_map_dataset",
    "check_new_stds",
    "check_suffix",
    "collect_map_names",
    "compute_absolute_time_granularity",
    "compute_relative_time_granularity",
    "core",
    "create_numeric_suffix",
    "create_suffix_from_datetime",
    "create_time_suffix",
    "dataset_factory",
    "dataset_mapcalculator",
    "datetime_after_steps",
    "datetime_math",
    "datetime_to_grass_datetime_string",
    "export_stds",
    "extract_dataset",
    "get_current_mapset",
    "get_dataset_list",
    "get_sql_template_path",
    "get_tgis_backend",
    "get_tgis_c_library_interface",
    "get_tgis_database",
    "get_tgis_database_string",
    "get_tgis_db_version_from_metadata",
    "get_tgis_message_interface",
    "get_tgis_metadata",
    "gran_singular_unit",
    "gran_to_gran",
    "import_stds",
    "increment_datetime_by_string",
    "init",
    "init_dbif",
    "list_maps_of_stds",
    "list_stds",
    "map_name_suffix",
    "next_cycle",
    "open_new_map_dataset",
    "open_new_stds",
    "open_old_stds",
    "option_to_datetime",
    "print_gridded_dataset_univar_statistics",
    "print_vector_dataset_univar_statistics",
    "profile_function",
    "register_map_object_list",
    "register_maps_in_space_time_dataset",
    "registered_maps_grouped",
    "sample_stds_by_stds_topology",
    "space_time_datasets",
    "stop_subprocesses",
    "string_to_datetime",
    "time_delta_to_relative_time",
    "tlist",
    "tlist_grouped",
    "upgrade_temporal_database",
]
