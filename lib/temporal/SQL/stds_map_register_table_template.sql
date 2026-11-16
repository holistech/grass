-- Create the table that lists the maps registered in one space-time dataset
--
-- The table is created once for each space-time dataset. The caller fills in
-- its name.
--
-- SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
-- SPDX-License-Identifier: GPL-2.0-or-later
--
-- Author: Soeren Gebbert

-- The ids of the maps registered in the dataset; the table does not depend on
-- the map type
CREATE TABLE SPACETIME_REGISTER_TABLE (
  id VARCHAR NOT NULL, -- This column is a primary key storing the ids of the registered maps
  PRIMARY KEY (id)
);
