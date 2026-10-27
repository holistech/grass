"""
Map layer and space time dataset classes

The six public classes state their kind and what is their own; the rest is in
the generic classes of datasets.py.

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import grass.script.array as garray

from .datasets import MapDataset, StdsDataset
from .kinds import KINDS


class _PlanarExtentMethods:
    """The spatial extent methods of the datasets that have no third dimension

    The mixin must come before the abstract base class in the list of bases,
    so that it provides the methods that AbstractDataset declares abstract.
    """

    def spatial_overlapping(self, dataset):
        """Return True if the spatial extents 2d overlap"""
        return self.spatial_extent.overlapping_2d(dataset.spatial_extent)

    def spatial_relation(self, dataset):
        """Return the two dimensional spatial relation"""
        return self.spatial_extent.spatial_relation_2d(dataset.spatial_extent)

    def spatial_intersection(self, dataset):
        """Return the two dimensional intersection as spatial_extent
        object or None in case no intersection was found.

        :param dataset: The abstract dataset to intersect with
        :return: The intersection spatial extent or None
        """
        return self.spatial_extent.intersect_2d(dataset.spatial_extent)

    def spatial_union(self, dataset):
        """Return the two dimensional union as spatial_extent
        object or None in case the extents does not overlap or meet.

        :param dataset: The abstract dataset to create a union with
        :return: The union spatial extent or None
        """
        return self.spatial_extent.union_2d(dataset.spatial_extent)

    def spatial_disjoint_union(self, dataset):
        """Return the two dimensional union as spatial_extent object.

        :param dataset: The abstract dataset to create a union with
        :return: The union spatial extent
        """
        return self.spatial_extent.disjoint_union_2d(dataset.spatial_extent)


class _VolumeExtentMethods:
    """The spatial extent methods of the datasets of 3D rasters

    They compute in space when the other dataset is a 3D raster map or a space
    time 3D raster dataset, and in the plane otherwise. Both 3D classes share
    the rule, so that a pair gives one answer in both directions. The mixin must
    come before the abstract base class, like _PlanarExtentMethods.
    """

    @staticmethod
    def _in_space(dataset):
        return dataset.get_type() in ("raster3d", "str3ds")

    def spatial_overlapping(self, dataset):
        """Return True if the spatial extents overlap"""
        if self._in_space(dataset):
            return self.spatial_extent.overlapping(dataset.spatial_extent)
        return self.spatial_extent.overlapping_2d(dataset.spatial_extent)

    def spatial_relation(self, dataset):
        """Return the two or three dimensional spatial relation"""
        if self._in_space(dataset):
            return self.spatial_extent.spatial_relation(dataset.spatial_extent)
        return self.spatial_extent.spatial_relation_2d(dataset.spatial_extent)

    def spatial_intersection(self, dataset):
        """Return the three or two dimensional intersection as spatial_extent
        object or None in case no intersection was found.

        :param dataset: The abstract dataset to intersect with
        :return: The intersection spatial extent or None
        """
        if self._in_space(dataset):
            return self.spatial_extent.intersect(dataset.spatial_extent)
        return self.spatial_extent.intersect_2d(dataset.spatial_extent)

    def spatial_union(self, dataset):
        """Return the three or two dimensional union as spatial_extent
        object or None in case the extents does not overlap or meet.

        :param dataset: The abstract dataset to create a union with
        :return: The union spatial extent or None
        """
        if self._in_space(dataset):
            return self.spatial_extent.union(dataset.spatial_extent)
        return self.spatial_extent.union_2d(dataset.spatial_extent)

    def spatial_disjoint_union(self, dataset):
        """Return the three or two dimensional union as spatial_extent object.

        :param dataset: The abstract dataset to create a union with
        :return: The union spatial extent
        """
        if self._in_space(dataset):
            return self.spatial_extent.disjoint_union(dataset.spatial_extent)
        return self.spatial_extent.disjoint_union_2d(dataset.spatial_extent)


class RasterDataset(_PlanarExtentMethods, MapDataset):
    """Raster dataset class

    This class provides functions to select, update, insert or delete raster
    map information and valid time stamps into the SQL temporal database.

    Usage:

    .. code-block:: pycon

        >>> import grass.script as gs
        >>> import grass.temporal as tgis
        >>> init()
        >>> gs.use_temp_region()
        >>> gs.run_command(
        ...     "g.region", n=80.0, s=0.0, e=120.0, w=0.0, t=1.0, b=0.0, res=10.0
        ... )
        >>> gs.run_command(
        ...     "r.mapcalc",
        ...     overwrite=True,
        ...     quiet=True,
        ...     expression="strds_map_test_case = 1",
        ... )
        >>> gs.run_command(
        ...     "r.timestamp", map="strds_map_test_case", date="15 jan 1999", quiet=True
        ... )
        >>> mapset = tgis.get_current_mapset()
        >>> name = "strds_map_test_case"
        >>> identifier = "%s@%s" % (name, mapset)
        >>> rmap = RasterDataset(identifier)
        >>> rmap.map_exists()
        True
        >>> rmap.read_timestamp_from_grass()
        True
        >>> rmap.get_temporal_extent_as_tuple()
        (datetime.datetime(1999, 1, 15, 0, 0), None)
        >>> rmap.load()
        True
        >>> rmap.spatial_extent.print_info()
         +-------------------- Spatial extent ----------------------------------------+
         | North:...................... 80.0
         | South:...................... 0.0
         | East:.. .................... 120.0
         | West:....................... 0.0
         | Top:........................ 0.0
         | Bottom:..................... 0.0
        >>> rmap.absolute_time.print_info()
         +-------------------- Absolute time -----------------------------------------+
         | Start time:................. 1999-01-15 00:00:00
         | End time:................... None
        >>> rmap.metadata.print_info()
         +-------------------- Metadata information ----------------------------------+
         | Datatype:................... CELL
         | Number of columns:.......... 12
         | Number of rows:............. 8
         | Number of cells:............ 96
         | North-South resolution:..... 10.0
         | East-west resolution:....... 10.0
         | Minimum value:.............. 1.0
         | Maximum value:.............. 1.0
         | Semantic label:............. None

        >>> gs.run_command(
        ...     "r.timestamp", map="strds_map_test_case", date="2 years", quiet=True
        ... )
        >>> rmap.read_timestamp_from_grass()
        True
        >>> rmap.get_temporal_extent_as_tuple()
        (2, None)
        >>> rmap.get_relative_time_unit()
        'years'
        >>> rmap.is_in_db()
        False
        >>> rmap.is_stds()
        False

        >>> newmap = rmap.get_new_instance("new@PERMANENT")
        >>> isinstance(newmap, RasterDataset)
        True
        >>> newstrds = rmap.get_new_stds_instance("new@PERMANENT")
        >>> isinstance(newstrds, SpaceTimeRasterDataset)
        True
        >>> rmap.get_type()
        'raster'
        >>> rmap.set_absolute_time(
        ...     start_time=datetime(2001, 1, 1), end_time=datetime(2012, 1, 1)
        ... )
        True
        >>> rmap.get_absolute_time()
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2012, 1, 1, 0, 0))
        >>> rmap.get_temporal_extent_as_tuple()
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2012, 1, 1, 0, 0))
        >>> rmap.get_name()
        'strds_map_test_case'
        >>> rmap.get_mapset() == mapset
        True
        >>> rmap.get_temporal_type()
        'absolute'
        >>> rmap.get_spatial_extent_as_tuple()
        (80.0, 0.0, 120.0, 0.0, 0.0, 0.0)
        >>> rmap.is_time_absolute()
        True
        >>> rmap.is_time_relative()
        False

        >>> gs.run_command("g.remove", flags="f", type="raster", name=name, quiet=True)
        >>> gs.del_temp_region()

    """

    kind = KINDS["raster"]

    def get_np_array(self):
        """Return this raster map as memmap numpy style array to access the raster
        values in numpy style without loading the whole map in the RAM.

        In case this raster map does exist in the grass spatial database,
        the map will be exported using r.out.bin to a temporary location
        and assigned to the memmap object that is returned by this function.

        In case the raster map does not exist, an empty temporary
        binary file will be created and assigned to the memap object.

        You need to call the write function to write the memmap
        array back into grass.
        """

        if self.map_exists():
            return garray.array(self.get_map_id())
        return garray.array()

    def read_semantic_label_from_grass(self) -> bool:
        """Read the semantic label of this map from the map metadata
        in the GRASS file system based spatial database and
        set the internal semantic label that should be inserted/updated
        in the temporal database.

        :return: True if success, False if semantic labels could not be
                 read (due to an error or because not being present)
        """

        semantic_label = self.ciface.read_raster_semantic_label(
            self.get_name(), self.get_mapset()
        )

        if not semantic_label:
            return False

        self.metadata.set_semantic_label(semantic_label)

        return True

    def write_semantic_label_to_grass(self) -> bool:
        """Write the semantic label of this map into the map metadata in
        the GRASS file system based spatial database.

        Internally the libgis API functions are used for writing

        :return: True if success, False on error
        """
        check = self.ciface.write_raster_semantic_label(
            self.get_name(), self.get_mapset(), self.metadata.get_semantic_label()
        )
        if check == -1:
            self.msgr.error(
                _("Unable to write semantic label for raster map <%s>")
                % (self.get_name())
            )
            return False

        return True

    def _fill_from_info(self, kvp) -> None:
        """Copy the extent and the metadata of the raster map info into this map"""
        self.set_spatial_extent_from_values(
            north=kvp["north"], south=kvp["south"], east=kvp["east"], west=kvp["west"]
        )

        self.metadata.set_nsres(kvp["nsres"])
        self.metadata.set_ewres(kvp["ewres"])
        self.metadata.set_datatype(kvp["datatype"])
        self.metadata.set_min(kvp["min"])
        self.metadata.set_max(kvp["max"])

        rows = int(kvp["rows"])
        cols = int(kvp["cols"])

        ncells = cols * rows

        self.metadata.set_cols(cols)
        self.metadata.set_rows(rows)
        self.metadata.set_number_of_cells(ncells)

        # Fill semantic label if defined
        semantic_label = self.ciface.read_raster_semantic_label(
            self.get_name(), self.get_mapset()
        )
        if semantic_label:
            self.metadata.set_semantic_label(semantic_label)

    def set_semantic_label(self, semantic_label) -> None:
        """Set semantic label identifier

        Metadata is updated in order to propagate semantic label into
        temporal DB.

        File-based semantic label stored in GRASS data base.

        :param str semantic_label: semantic label (eg. S2_1)
        """
        self.metadata.set_semantic_label(semantic_label)
        self.write_semantic_label_to_grass()


class Raster3DDataset(_VolumeExtentMethods, MapDataset):
    """Raster3d dataset class

    This class provides functions to select, update, insert or delete raster3d
    map information and valid time stamps into the SQL temporal database.

    Usage:

    .. code-block:: pycon

        >>> import grass.script as gs
        >>> init()
        >>> gs.use_temp_region()
        >>> gs.run_command(
        ...     "g.region",
        ...     n=80.0,
        ...     s=0.0,
        ...     e=120.0,
        ...     w=0.0,
        ...     t=100.0,
        ...     b=0.0,
        ...     res=10.0,
        ...     res3=10.0,
        ... )
        >>> gs.run_command(
        ...     "r3.mapcalc",
        ...     overwrite=True,
        ...     quiet=True,
        ...     expression="str3ds_map_test_case = 1",
        ... )
        >>> gs.run_command(
        ...     "r3.timestamp",
        ...     map="str3ds_map_test_case",
        ...     date="15 jan 1999",
        ...     quiet=True,
        ... )
        >>> mapset = get_current_mapset()
        >>> name = "str3ds_map_test_case"
        >>> identifier = "%s@%s" % (name, mapset)
        >>> r3map = Raster3DDataset(identifier)
        >>> r3map.map_exists()
        True
        >>> r3map.read_timestamp_from_grass()
        True
        >>> r3map.get_temporal_extent_as_tuple()
        (datetime.datetime(1999, 1, 15, 0, 0), None)
        >>> r3map.load()
        True
        >>> r3map.spatial_extent.print_info()
         +-------------------- Spatial extent ----------------------------------------+
         | North:...................... 80.0
         | South:...................... 0.0
         | East:.. .................... 120.0
         | West:....................... 0.0
         | Top:........................ 100.0
         | Bottom:..................... 0.0
        >>> r3map.absolute_time.print_info()
         +-------------------- Absolute time -----------------------------------------+
         | Start time:................. 1999-01-15 00:00:00
         | End time:................... None
        >>> r3map.metadata.print_info()
         +-------------------- Metadata information ----------------------------------+
         | Datatype:................... DCELL
         | Number of columns:.......... 12
         | Number of rows:............. 8
         | Number of cells:............ 960
         | North-South resolution:..... 10.0
         | East-west resolution:....... 10.0
         | Minimum value:.............. 1.0
         | Maximum value:.............. 1.0
         | Number of depths:........... 10
         | Top-Bottom resolution:...... 10.0

        >>> gs.run_command(
        ...     "r3.timestamp", map="str3ds_map_test_case", date="2 years", quiet=True
        ... )
        >>> r3map.read_timestamp_from_grass()
        True
        >>> r3map.get_temporal_extent_as_tuple()
        (2, None)
        >>> r3map.get_relative_time_unit()
        'years'
        >>> r3map.is_in_db()
        False
        >>> r3map.is_stds()
        False

        >>> newmap = r3map.get_new_instance("new@PERMANENT")
        >>> isinstance(newmap, Raster3DDataset)
        True
        >>> newstr3ds = r3map.get_new_stds_instance("new@PERMANENT")
        >>> isinstance(newstr3ds, SpaceTimeRaster3DDataset)
        True
        >>> r3map.get_type()
        'raster3d'
        >>> r3map.set_absolute_time(
        ...     start_time=datetime(2001, 1, 1), end_time=datetime(2012, 1, 1)
        ... )
        True
        >>> r3map.get_absolute_time()
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2012, 1, 1, 0, 0))
        >>> r3map.get_temporal_extent_as_tuple()
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2012, 1, 1, 0, 0))
        >>> r3map.get_name()
        'str3ds_map_test_case'
        >>> r3map.get_mapset() == mapset
        True
        >>> r3map.get_temporal_type()
        'absolute'
        >>> r3map.get_spatial_extent_as_tuple()
        (80.0, 0.0, 120.0, 0.0, 100.0, 0.0)
        >>> r3map.is_time_absolute()
        True
        >>> r3map.is_time_relative()
        False
        >>> gs.run_command(
        ...     "g.remove", flags="f", type="raster_3d", name=name, quiet=True
        ... )
        >>> gs.del_temp_region()

    """

    kind = KINDS["raster3d"]

    def get_np_array(self):
        """Return this 3D raster map as memmap numpy style array to access the
        3D raster values in numpy style without loading the whole map in
        the RAM.

        In case this 3D raster map does exist in the grass spatial database,
        the map will be exported using r3.out.bin to a temporary location
        and assigned to the memmap object that is returned by this function.

        In case the 3D raster map does not exist, an empty temporary
        binary file will be created and assigned to the memap object.

        You need to call the write function to write the memmap
        array back into grass.
        """

        if self.map_exists():
            return garray.array3d(self.get_map_id())
        return garray.array3d()

    def _fill_from_info(self, kvp) -> None:
        """Copy the extent and the metadata of the 3D raster map info into this map"""
        self.set_spatial_extent_from_values(
            north=kvp["north"],
            south=kvp["south"],
            east=kvp["east"],
            west=kvp["west"],
            top=kvp["top"],
            bottom=kvp["bottom"],
        )

        self.metadata.set_nsres(kvp["nsres"])
        self.metadata.set_ewres(kvp["ewres"])
        self.metadata.set_tbres(kvp["tbres"])
        self.metadata.set_datatype(kvp["datatype"])
        self.metadata.set_min(kvp["min"])
        self.metadata.set_max(kvp["max"])

        rows = int(kvp["rows"])
        cols = int(kvp["cols"])
        depths = int(kvp["depths"])

        ncells = cols * rows * depths

        self.metadata.set_cols(cols)
        self.metadata.set_rows(rows)
        self.metadata.set_depths(depths)
        self.metadata.set_number_of_cells(ncells)


class VectorDataset(_PlanarExtentMethods, MapDataset):
    """Vector dataset class

    This class provides functions to select, update, insert or delete vector
    map information and valid time stamps into the SQL temporal database.

    Usage:

    .. code-block:: pycon

        >>> import grass.script as gs
        >>> init()
        >>> gs.use_temp_region()
        >>> gs.run_command(
        ...     "g.region", n=80.0, s=0.0, e=120.0, w=0.0, t=1.0, b=0.0, res=10.0
        ... )
        >>> gs.run_command(
        ...     "v.random",
        ...     overwrite=True,
        ...     output="stvds_map_test_case",
        ...     n=100,
        ...     zmin=0,
        ...     zmax=100,
        ...     flags="z",
        ...     column="elevation",
        ...     quiet=True,
        ... )
        >>> gs.run_command(
        ...     "v.timestamp", map="stvds_map_test_case", date="15 jan 1999", quiet=True
        ... )
        >>> mapset = get_current_mapset()
        >>> name = "stvds_map_test_case"
        >>> identifier = "%s@%s" % (name, mapset)
        >>> vmap = VectorDataset(identifier)
        >>> vmap.map_exists()
        True
        >>> vmap.read_timestamp_from_grass()
        True
        >>> vmap.get_temporal_extent_as_tuple()
        (datetime.datetime(1999, 1, 15, 0, 0), None)
        >>> vmap.load()
        True
        >>> vmap.absolute_time.print_info()
         +-------------------- Absolute time -----------------------------------------+
         | Start time:................. 1999-01-15 00:00:00
         | End time:................... None
        >>> vmap.metadata.print_info()
         +-------------------- Metadata information ----------------------------------+
         | Is map 3d .................. True
         | Number of points ........... 100
         | Number of lines ............ 0
         | Number of boundaries ....... 0
         | Number of centroids ........ 0
         | Number of faces ............ 0
         | Number of kernels .......... 0
         | Number of primitives ....... 100
         | Number of nodes ............ 0
         | Number of areas ............ 0
         | Number of islands .......... 0
         | Number of holes ............ 0
         | Number of volumes .......... 0

        >>> gs.run_command(
        ...     "v.timestamp", map="stvds_map_test_case", date="2 years", quiet=True
        ... )
        >>> vmap.read_timestamp_from_grass()
        True
        >>> vmap.get_temporal_extent_as_tuple()
        (2, None)
        >>> vmap.get_relative_time_unit()
        'years'
        >>> vmap.is_in_db()
        False
        >>> vmap.is_stds()
        False

        >>> newmap = vmap.get_new_instance("new@PERMANENT")
        >>> isinstance(newmap, VectorDataset)
        True
        >>> newstvds = vmap.get_new_stds_instance("new@PERMANENT")
        >>> isinstance(newstvds, SpaceTimeVectorDataset)
        True
        >>> vmap.get_type()
        'vector'
        >>> vmap.set_absolute_time(
        ...     start_time=datetime(2001, 1, 1), end_time=datetime(2012, 1, 1)
        ... )
        True
        >>> vmap.get_absolute_time()
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2012, 1, 1, 0, 0))
        >>> vmap.get_temporal_extent_as_tuple()
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2012, 1, 1, 0, 0))
        >>> vmap.get_name()
        'stvds_map_test_case'
        >>> vmap.get_mapset() == mapset
        True
        >>> vmap.get_temporal_type()
        'absolute'
        >>> vmap.is_time_absolute()
        True
        >>> vmap.is_time_relative()
        False
        >>> gs.run_command("g.remove", flags="f", type="vector", name=name, quiet=True)
        >>> gs.del_temp_region()

    """

    kind = KINDS["vector"]

    def get_layer(self):
        """Return the layer"""
        return self.base.get_layer()

    def _fill_from_info(self, kvp) -> None:
        """Copy the extent and the metadata of the vector map info into this map"""
        self.set_spatial_extent_from_values(
            north=kvp["north"],
            south=kvp["south"],
            east=kvp["east"],
            west=kvp["west"],
            top=kvp["top"],
            bottom=kvp["bottom"],
        )

        self.metadata.set_3d_info(kvp["map3d"])
        self.metadata.set_number_of_points(kvp["points"])
        self.metadata.set_number_of_lines(kvp["lines"])
        self.metadata.set_number_of_boundaries(kvp["boundaries"])
        self.metadata.set_number_of_centroids(kvp["centroids"])
        self.metadata.set_number_of_faces(kvp["faces"])
        self.metadata.set_number_of_kernels(kvp["kernels"])
        self.metadata.set_number_of_primitives(kvp["primitives"])
        self.metadata.set_number_of_nodes(kvp["nodes"])
        self.metadata.set_number_of_areas(kvp["areas"])
        self.metadata.set_number_of_islands(kvp["islands"])
        self.metadata.set_number_of_holes(kvp["holes"])
        self.metadata.set_number_of_volumes(kvp["volumes"])


class SpaceTimeRasterDataset(_PlanarExtentMethods, StdsDataset):
    """Space time raster dataset class

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> mapset = tgis.get_current_mapset()
        >>> strds = tgis.SpaceTimeRasterDataset("old@%s" % mapset)
        >>> strds.is_in_db()
        False
        >>> strds.is_stds()
        True
        >>> strds.get_type()
        'strds'
        >>> newstrds = strds.get_new_instance("newstrds@%s" % mapset)
        >>> isinstance(newstrds, SpaceTimeRasterDataset)
        True
        >>> newmap = strds.get_new_map_instance("newmap@%s" % mapset)
        >>> isinstance(newmap, RasterDataset)
        True
        >>> strds.reset("new@%s" % mapset)
        >>> strds.is_in_db()
        False
        >>> strds.reset(None)
        >>> strds.is_in_db()
        False
        >>> strds.get_id()

    ...
    """

    kind = KINDS["strds"]

    def set_semantic_label(self, semantic_label) -> None:
        """Set semantic label

        :param str semantic_label: semantic label (eg. S2_1)
        """
        self.semantic_label = semantic_label


class SpaceTimeRaster3DDataset(_VolumeExtentMethods, StdsDataset):
    """Space time raster3d dataset class

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> mapset = tgis.get_current_mapset()
        >>> str3ds = tgis.space_time_datasets.SpaceTimeRaster3DDataset(
        ...     "old@%s" % mapset
        ... )
        >>> str3ds.is_in_db()
        False
        >>> str3ds.is_stds()
        True
        >>> str3ds.get_type()
        'str3ds'
        >>> newstrds = str3ds.get_new_instance("newstrds@%s" % mapset)
        >>> isinstance(newstrds, SpaceTimeRaster3DDataset)
        True
        >>> newmap = str3ds.get_new_map_instance("newmap@%s" % mapset)
        >>> isinstance(newmap, Raster3DDataset)
        True
        >>> str3ds.reset("new@%s" % mapset)
        >>> str3ds.is_in_db()
        False
        >>> str3ds.reset(None)
        >>> str3ds.is_in_db()
        False
        >>> str3ds.get_id()

    ...
    """

    kind = KINDS["str3ds"]


class SpaceTimeVectorDataset(_PlanarExtentMethods, StdsDataset):
    """Space time vector dataset class

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> mapset = tgis.get_current_mapset()
        >>> stvds = tgis.space_time_datasets.SpaceTimeVectorDataset("old@%s" % mapset)
        >>> stvds.is_in_db()
        False
        >>> stvds.is_stds()
        True
        >>> stvds.get_type()
        'stvds'
        >>> newstvds = stvds.get_new_instance("newstvds@%s" % mapset)
        >>> isinstance(newstvds, SpaceTimeVectorDataset)
        True
        >>> newmap = stvds.get_new_map_instance("newmap@%s" % mapset)
        >>> isinstance(newmap, VectorDataset)
        True
        >>> stvds.reset("new@%s" % mapset)
        >>> stvds.is_in_db()
        False
        >>> stvds.reset(None)
        >>> stvds.is_in_db()
        False
        >>> stvds.get_id()

    ...
    """

    kind = KINDS["stvds"]
