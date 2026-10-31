-- Create the views of raster maps that join all of their tables
--
-- SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Soeren Gebbert
--
-- A map appears in a view only if it has a row in each of the five tables that
-- the view joins (base data, time, spatial extent, metadata and register
-- table). A map that lacks one of the rows is in no list but is still counted
-- in number_of_maps of its dataset.

-- Create the views to access all cols for the absolute and relative time

CREATE VIEW raster_view_abs_time AS SELECT
            A1.id, A1.mapset,
            A1.name, A1.temporal_type,
            A1.creation_time,
            A1.creator,
            A2.start_time, A2.end_time,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.datatype, A4.cols, A4.rows,
            A4.nsres, A4.ewres, A4.min, A4.max,
            A4.number_of_cells, A4.semantic_label, A5.registered_stds
            FROM raster_base A1, raster_absolute_time A2,
            raster_spatial_extent A3, raster_metadata A4,
            raster_stds_register A5
            WHERE A1.id = A2.id AND A1.id = A3.id AND
            A1.id = A4.id AND A1.id = A5.id;

CREATE VIEW raster_view_rel_time AS SELECT
            A1.id, A1.mapset,
            A1.name, A1.temporal_type,
            A1.creation_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.unit,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.datatype, A4.cols, A4.rows,
            A4.nsres, A4.ewres, A4.min, A4.max,
            A4.number_of_cells, A4.semantic_label, A5.registered_stds
            FROM raster_base A1, raster_relative_time A2,
            raster_spatial_extent A3, raster_metadata A4,
            raster_stds_register A5
            WHERE A1.id = A2.id AND A1.id = A3.id AND
            A1.id = A4.id AND A1.id = A5.id;
