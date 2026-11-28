-- Create the metadata table of raster maps
--
-- SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Soeren Gebbert

-- The metadata table reflects most of the raster metadata available in grass

CREATE TABLE raster_metadata (
  id VARCHAR NOT NULL,               -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  datatype VARCHAR NOT NULL,
  cols INTEGER NOT NULL,
  rows INTEGER NOT NULL,
  number_of_cells INTEGER NOT NULL,
  nsres DOUBLE PRECISION NOT NULL,
  ewres DOUBLE PRECISION NOT NULL,
  min DOUBLE PRECISION,
  max DOUBLE PRECISION,
  semantic_label VARCHAR,
  PRIMARY KEY (id)
);
