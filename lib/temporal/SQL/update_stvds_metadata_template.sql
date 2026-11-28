-- Update the feature and topology counts of a space-time vector dataset from
-- its maps
--
-- SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Soeren Gebbert
-- UPDATE FROM syntax: Stefan Blumentrath

-- The caller fills in the name of the map register table of the dataset and the
-- dataset id as an SQL literal: 'name@mapset'.

-- Update the vector features and topology
UPDATE stvds_metadata
   SET
       points = new_stats.points_new,
       lines = new_stats.lines_new,
       boundaries = new_stats.boundaries_new,
       centroids = new_stats.centroids_new,
       faces = new_stats.faces_new,
       kernels = new_stats.kernels_new,
       primitives = new_stats.primitives_new,
       nodes = new_stats.nodes_new,
       areas = new_stats.areas_new,
       islands = new_stats.islands_new,
       holes = new_stats.holes_new,
       volumes = new_stats.volumes_new
  FROM
       (SELECT
           sum(points) AS points_new,
           sum(lines) AS lines_new,
           sum(boundaries) AS boundaries_new,
           sum(centroids) AS centroids_new,
           sum(faces) AS faces_new,
           sum(kernels) AS kernels_new,
           sum(primitives) AS primitives_new,
           sum(nodes) AS nodes_new,
           sum(areas) AS areas_new,
           sum(islands) AS islands_new,
           sum(holes) AS holes_new,
           sum(volumes) AS volumes_new
       FROM
           SPACETIME_REGISTER_TABLE INNER JOIN
           vector_metadata ON
           SPACETIME_REGISTER_TABLE.id = vector_metadata.id
       ) AS new_stats
 WHERE stvds_metadata.id = SPACETIME_ID;
