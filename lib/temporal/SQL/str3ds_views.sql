-- Create the views of space-time 3D raster datasets that join all of their tables
--
-- SPDX-FileCopyrightText: 2013-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Soeren Gebbert
--
-- A dataset appears in a view only if it has a row in each of the four tables
-- that the view joins (base data, time, spatial extent and metadata). A dataset
-- that lacks one of the rows is in no list.

-- Create the views to access all cols for absolute or relative time

CREATE VIEW str3ds_view_abs_time AS SELECT
            A1.id, A1.name, A1.mapset, A1.temporal_type,
            A1.semantic_type,
            A1.creation_time, A1.modification_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.granularity,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.raster3d_register,
            A4.number_of_maps,
            A4.nsres_min, A4.ewres_min,
            A4.nsres_max, A4.ewres_max,
            A4.tbres_min, A4.tbres_max,
            A4.min_min, A4.min_max,
            A4.max_min, A4.max_max, A4.aggregation_type,
            A4.title, A4.description, A4.command
            FROM str3ds_base A1, str3ds_absolute_time A2,
            str3ds_spatial_extent A3, str3ds_metadata A4 WHERE A1.id = A2.id AND
            A1.id = A3.id AND A1.id = A4.id;

CREATE VIEW str3ds_view_rel_time AS SELECT
            A1.id, A1.name, A1.mapset, A1.temporal_type,
            A1.semantic_type,
            A1.creation_time, A1.modification_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.unit, A2.granularity,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.raster3d_register,
            A4.number_of_maps,
            A4.nsres_min, A4.ewres_min,
            A4.nsres_max, A4.ewres_max,
            A4.tbres_min, A4.tbres_max,
            A4.min_min, A4.min_max,
            A4.max_min, A4.max_max, A4.aggregation_type,
            A4.title, A4.description, A4.command
            FROM str3ds_base A1, str3ds_relative_time A2,
            str3ds_spatial_extent A3, str3ds_metadata A4 WHERE A1.id = A2.id AND
            A1.id = A3.id AND A1.id = A4.id;
