"""The temporal framework of GRASS

The package exports the names that code outside the library uses, listed in
``__all__``; the contract test ``grass_temporal_public_contract_test.py`` holds
the list and who uses each name. Everything else is imported from its module,
for example ``from grass.temporal.related_maps import related_per_granule``.
"""

from grass.exceptions import FatalError

from . import core, datetime_math, list_stds, space_time_datasets
from .abstract_space_time_dataset import AbstractSpaceTimeDataset
from .aggregation import aggregate_raster_maps, collect_map_names
from .algebra.parser.facade import (
    TemporalRaster3DAlgebraParser,
    TemporalRasterAlgebraParser,
    TemporalVectorAlgebraParser,
)
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
    SpaceTimeRasterDataset,
    VectorDataset,
)
from .topology import SpatioTemporalTopologyBuilder
from .stds_export import export_stds
from .stds_import import import_stds
from .classic.temporal_raster_base_algebra import TemporalRasterAlgebraLexer
from .temporal_extent import AbsoluteTemporalExtent, RelativeTemporalExtent
from .temporal_granularity import (
    check_granularity_string,
    compute_absolute_time_granularity,
    compute_relative_time_granularity,
    gran_singular_unit,
    gran_to_gran,
)
from .tool_steps import (
    dataset_cycles,
    first_related_map_id,
    names_from_file,
    open_new_map_for,
    open_result_map,
    register_in_new_stds,
    register_new_maps,
    remove_maps,
)
from .univar_statistics import (
    print_gridded_dataset_univar_statistics,
    print_vector_dataset_univar_statistics,
)

__all__ = [
    "AbsoluteTemporalExtent",
    "AbstractSpaceTimeDataset",
    "FatalError",
    "Raster3DDataset",
    "RasterDataset",
    "RelativeTemporalExtent",
    "SQLDatabaseInterfaceConnection",
    "SQLStatementError",
    "SpaceTimeRasterDataset",
    "SpatioTemporalTopologyBuilder",
    "TemporalRaster3DAlgebraParser",
    "TemporalRasterAlgebraLexer",
    "TemporalRasterAlgebraParser",
    "TemporalVectorAlgebraParser",
    "VectorDataset",
    "adjust_datetime_to_granularity",
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
    "dataset_cycles",
    "dataset_factory",
    "dataset_mapcalculator",
    "datetime_after_steps",
    "datetime_math",
    "datetime_to_grass_datetime_string",
    "export_stds",
    "extract_dataset",
    "first_related_map_id",
    "get_current_mapset",
    "get_dataset_list",
    "get_sql_template_path",
    "get_tgis_c_library_interface",
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
    "names_from_file",
    "next_cycle",
    "open_new_map_dataset",
    "open_new_map_for",
    "open_new_stds",
    "open_old_stds",
    "open_result_map",
    "option_to_datetime",
    "print_gridded_dataset_univar_statistics",
    "print_vector_dataset_univar_statistics",
    "profile_function",
    "register_in_new_stds",
    "register_map_object_list",
    "register_maps_in_space_time_dataset",
    "register_new_maps",
    "registered_maps_grouped",
    "remove_maps",
    "sample_stds_by_stds_topology",
    "space_time_datasets",
    "stop_subprocesses",
    "string_to_datetime",
    "time_delta_to_relative_time",
    "tlist",
    "tlist_grouped",
    "upgrade_temporal_database",
]
