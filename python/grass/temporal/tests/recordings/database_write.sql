CREATE TABLE "raster_map_register_a9ad879a5ba0038ca0ea7257d239a0d1" (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_absolute_time (
  id VARCHAR NOT NULL,   -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  start_time TIMESTAMP,  --  Start of the valid time, can be NULL if no time information is available
  end_time TIMESTAMP,    --  End of the valid time, can be NULL if no time information is available or valid time is a single point in time
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_base (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name (layer) and mapset (name(:layer)@mapset) and is used as primary key
  name VARCHAR NOT NULL,                -- name of the grass map
  mapset VARCHAR NOT NULL,              -- mapset of the grass map
  layer VARCHAR,                        -- The layer id of the map, this is currently only in use by vector maps
  creator VARCHAR NOT NULL,
  temporal_type VARCHAR,                -- The temporal type of the grass map "absolute" or "relative" or NULL in case no time stamp is available
  creation_time TIMESTAMP NOT NULL,      -- The time of creation of the grass map
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_map_register_7f402c6f1a3eb2af4c63c569ee489d93 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_metadata (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  datatype VARCHAR NOT NULL,
  cols INTEGER NOT NULL,
  rows INTEGER NOT NULL,
  depths INTEGER NOT NULL,
  number_of_cells INTEGER NOT NULL,
  nsres DOUBLE PRECISION NOT NULL,
  ewres DOUBLE PRECISION NOT NULL,
  tbres DOUBLE PRECISION NOT NULL,
  min DOUBLE PRECISION,
  max DOUBLE PRECISION,
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_relative_time (
  id VARCHAR NOT NULL,          -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary foreign key
  start_time INTEGER,  -- The relative valid start time in
  end_time INTEGER,    -- The relative valid end time in
  unit VARCHAR,                 -- The relative time unit, available are "years, months, days, minutes, seconds"
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_spatial_extent (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  -- below is the spatial extent of the map
  north DOUBLE PRECISION NOT NULL,
  south DOUBLE PRECISION NOT NULL,
  east DOUBLE PRECISION NOT NULL,
  west DOUBLE PRECISION NOT NULL,
  top DOUBLE PRECISION NOT NULL,
  bottom DOUBLE PRECISION NOT NULL,
  proj VARCHAR,
  PRIMARY KEY (id)
);
CREATE TABLE raster3d_stds_register (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name (layer) and mapset (name(:layer)@mapset) and is used as primary key
  registered_stds VARCHAR,              -- This column stores the names of all space time datasets in which a specific map is registered
  PRIMARY KEY (id)
);
CREATE TABLE raster_absolute_time (
  id VARCHAR NOT NULL,   -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  start_time TIMESTAMP,  --  Start of the valid time, can be NULL if no time information is available
  end_time TIMESTAMP,    --  End of the valid time, can be NULL if no time information is available or valid time is a single point in time
  PRIMARY KEY (id)
);
CREATE TABLE raster_base (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name (layer) and mapset (name(:layer)@mapset) and is used as primary key
  name VARCHAR NOT NULL,                -- name of the grass map
  mapset VARCHAR NOT NULL,              -- mapset of the grass map
  layer VARCHAR,                        -- The layer id of the map, this is currently only in use by vector maps
  creator VARCHAR NOT NULL,
  temporal_type VARCHAR,                -- The temporal type of the grass map "absolute" or "relative" or NULL in case no time stamp is available
  creation_time TIMESTAMP NOT NULL,      -- The time of creation of the grass map
  PRIMARY KEY (id)
);
CREATE TABLE raster_map_register_22e3c261135396136fb4632c4a1f5601 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster_map_register_61faa24dfaecfe07b7c99ea4666187c8 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster_map_register_638463c28b29c46ee1ff78f2993f2bc1 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster_map_register_a9894a19e40d453484aac2241aa57ab7 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster_map_register_f258237acb32c393a438f22c9634201b (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE raster_metadata (
  id VARCHAR NOT NULL,               -- The id (PFK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
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
CREATE TABLE raster_relative_time (
  id VARCHAR NOT NULL,          -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary foreign key
  start_time INTEGER,  -- The relative valid start time in
  end_time INTEGER,    -- The relative valid end time in
  unit VARCHAR,                 -- The relative time unit, available are "years, months, days, minutes, seconds"
  PRIMARY KEY (id)
);
CREATE TABLE raster_spatial_extent (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  -- below is the spatial extent of the map
  north DOUBLE PRECISION NOT NULL,
  south DOUBLE PRECISION NOT NULL,
  east DOUBLE PRECISION NOT NULL,
  west DOUBLE PRECISION NOT NULL,
  top DOUBLE PRECISION NOT NULL,
  bottom DOUBLE PRECISION NOT NULL,
  proj VARCHAR,
  PRIMARY KEY (id)
);
CREATE TABLE raster_stds_register (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name (layer) and mapset (name(:layer)@mapset) and is used as primary key
  registered_stds VARCHAR,              -- This column stores the names of all space time datasets in which a specific map is registered
  PRIMARY KEY (id)
);
CREATE TABLE str3ds_absolute_time (
  id VARCHAR NOT NULL,            -- Id of the space-time dataset, this is the primary key
  start_time TIMESTAMP,           -- Start of the valid time, can be NULL if no map is registered
  end_time TIMESTAMP,             -- End of the valid time, can be NULL if no map is registered
  granularity VARCHAR,            -- The granularity "NNN seconds, NNN minutes, NNN hours, NNN days, NNN months, NNN years"
  map_time VARCHAR,               -- The temporal type of the registered maps, may be interval, point or mixed
  PRIMARY KEY (id)
);
CREATE TABLE str3ds_base (
  id VARCHAR NOT NULL,                 -- Id of the space-time dataset, name@mapset this is the primary key
  name VARCHAR NOT NULL,               -- name of the space-time dataset
  mapset VARCHAR NOT NULL,             -- mapset of the space-time dataset
  creator VARCHAR NOT NULL,            -- Name of the creator
  temporal_type VARCHAR NOT NULL,      -- The temporal type of the dataset "absolute" or "relative"
  semantic_type VARCHAR NOT NULL,      -- The semantic data description used for aggregation/decomposition algorithm selection: min, max, mean or sum
  creation_time TIMESTAMP NOT NULL,    -- The time of creation of the space-time dataset
  modification_time TIMESTAMP NOT NULL,-- The time of the last modification of the space time dataset
  PRIMARY KEY (id)
);
CREATE TABLE str3ds_metadata (
  id VARCHAR NOT NULL,          -- Id of the space time 3D raster dataset, this is the primary key
  raster3d_register VARCHAR,    -- The id of the table in which the 3D raster maps are registered for this dataset
  number_of_maps INTEGER,       -- The number of registered 3D raster maps
  max_min DOUBLE PRECISION,     -- The minimal maximum of the registered 3D raster maps
  min_min DOUBLE PRECISION,     -- The minimal minimum of the registered 3D raster maps
  max_max DOUBLE PRECISION,     -- The maximal maximum of the registered 3D raster maps
  min_max DOUBLE PRECISION,     -- The maximal minimum of the registered 3D raster maps
  nsres_min DOUBLE PRECISION,   -- The lowest north-south resolution of the registered 3D raster maps
  nsres_max DOUBLE PRECISION,   -- The highest north-south resolution of the registered 3D raster maps
  ewres_min DOUBLE PRECISION,   -- The lowest east-west resolution of the registered 3D raster maps
  ewres_max DOUBLE PRECISION,   -- The highest east-west resolution of the registered 3D raster maps
  tbres_min DOUBLE PRECISION,   -- The lowest top-bottom resolution of the registered 3D raster maps
  tbres_max DOUBLE PRECISION,   -- The highest top-bottom resolution of the registered 3D raster maps
  aggregation_type VARCHAR,     -- The aggregation type of the dataset (mean, min, max, ...) set by aggregation modules
  title VARCHAR,                -- Title of the space time 3D raster dataset
  description VARCHAR,          -- Detailed description of the space time 3D raster dataset
  command VARCHAR,              -- The command that was used to create the space time 3D raster dataset
  PRIMARY KEY (id)
);
CREATE TABLE str3ds_relative_time (
  id VARCHAR NOT NULL,            -- Id of the space-time dataset, this is the primary key
  start_time INTEGER,             -- The relative valid start time
  end_time INTEGER,               -- The relative valid end time
  granularity INTEGER,            -- The granularity
  unit VARCHAR,                   -- The relative time unit, available are "years, months, days, minutes, seconds"
  map_time VARCHAR,               -- The temporal type of the registered maps, may be interval, point or mixed
  PRIMARY KEY (id)
);
CREATE TABLE str3ds_spatial_extent (
  id VARCHAR NOT NULL,      -- Id of the space-time dataset, this is the primary key
  north DOUBLE PRECISION,   -- The spatial north extent, derived from the registered maps
  south DOUBLE PRECISION,   -- The spatial south extent, derived from the registered maps
  east DOUBLE PRECISION,    -- The spatial east extent, derived from the registered maps
  west DOUBLE PRECISION,    -- The spatial west extent, derived from the registered maps
  top DOUBLE PRECISION,     -- The spatial top extent, derived from the registered maps
  bottom DOUBLE PRECISION,  -- The spatial bottom extent, derived from the registered maps
  proj VARCHAR,      -- The projection of the space time dataset (XY of LL)
  PRIMARY KEY (id)
);
CREATE TABLE strds_absolute_time (
  id VARCHAR NOT NULL,            -- Id of the space-time dataset, this is the primary key
  start_time TIMESTAMP,           -- Start of the valid time, can be NULL if no map is registered
  end_time TIMESTAMP,             -- End of the valid time, can be NULL if no map is registered
  granularity VARCHAR,            -- The granularity "NNN seconds, NNN minutes, NNN hours, NNN days, NNN months, NNN years"
  map_time VARCHAR,               -- The temporal type of the registered maps, may be interval, point or mixed
  PRIMARY KEY (id)
);
CREATE TABLE strds_base (
  id VARCHAR NOT NULL,                 -- Id of the space-time dataset, name@mapset this is the primary key
  name VARCHAR NOT NULL,               -- name of the space-time dataset
  mapset VARCHAR NOT NULL,             -- mapset of the space-time dataset
  creator VARCHAR NOT NULL,            -- Name of the creator
  temporal_type VARCHAR NOT NULL,      -- The temporal type of the dataset "absolute" or "relative"
  semantic_type VARCHAR NOT NULL,      -- The semantic data description used for aggregation/decomposition algorithm selection: min, max, mean or sum
  creation_time TIMESTAMP NOT NULL,    -- The time of creation of the space-time dataset
  modification_time TIMESTAMP NOT NULL,-- The time of the last modification of the space time dataset
  PRIMARY KEY (id)
);
CREATE TABLE strds_metadata (
  id VARCHAR NOT NULL,          -- Id of the space-time dataset, this is the primary key
  raster_register VARCHAR,      -- The id of the table in which the raster maps are registered for this dataset
  number_of_maps INTEGER,       -- The number of registered raster maps
  max_min DOUBLE PRECISION,     -- The minimal maximum of the registered raster maps
  min_min DOUBLE PRECISION,     -- The minimal minimum of the registered raster maps
  max_max DOUBLE PRECISION,     -- The maximal maximum of the registered raster maps
  min_max DOUBLE PRECISION,     -- The maximal minimum of the registered raster maps
  nsres_min DOUBLE PRECISION,   -- The lowest north-south resolution of the registered raster maps
  nsres_max DOUBLE PRECISION,   -- The highest north-south resolution of the registered raster maps
  ewres_min DOUBLE PRECISION,   -- The lowest east-west resolution of the registered raster maps
  ewres_max DOUBLE PRECISION,   -- The highest east-west resolution of the registered raster maps
  aggregation_type VARCHAR,     -- The aggregation type of the dataset (mean, min, max, ...) set by aggregation modules
  number_of_semantic_labels INTEGER,       -- The number of registered semantic labels
  title VARCHAR,                -- Title of the space-time raster dataset
  description VARCHAR,          -- Detailed description of the space-time raster dataset
  command VARCHAR,              -- The command that was used to create the space time raster dataset
  PRIMARY KEY (id)
);
CREATE TABLE strds_relative_time (
  id VARCHAR NOT NULL,            -- Id of the space-time dataset, this is the primary key
  start_time INTEGER,             -- The relative valid start time
  end_time INTEGER,               -- The relative valid end time
  granularity INTEGER,            -- The granularity
  unit VARCHAR,                   -- The relative time unit, available are "years, months, days, minutes, seconds"
  map_time VARCHAR,               -- The temporal type of the registered maps, may be interval, point or mixed
  PRIMARY KEY (id)
);
CREATE TABLE strds_spatial_extent (
  id VARCHAR NOT NULL,      -- Id of the space-time dataset, this is the primary key
  north DOUBLE PRECISION,   -- The spatial north extent, derived from the registered maps
  south DOUBLE PRECISION,   -- The spatial south extent, derived from the registered maps
  east DOUBLE PRECISION,    -- The spatial east extent, derived from the registered maps
  west DOUBLE PRECISION,    -- The spatial west extent, derived from the registered maps
  top DOUBLE PRECISION,     -- The spatial top extent, derived from the registered maps
  bottom DOUBLE PRECISION,  -- The spatial bottom extent, derived from the registered maps
  proj VARCHAR,      -- The projection of the space time dataset (XY of LL)
  PRIMARY KEY (id)
);
CREATE TABLE stvds_absolute_time (
  id VARCHAR NOT NULL,            -- Id of the space-time dataset, this is the primary key
  start_time TIMESTAMP,           -- Start of the valid time, can be NULL if no map is registered
  end_time TIMESTAMP,             -- End of the valid time, can be NULL if no map is registered
  granularity VARCHAR,            -- The granularity "NNN seconds, NNN minutes, NNN hours, NNN days, NNN months, NNN years"
  map_time VARCHAR,               -- The temporal type of the registered maps, may be interval, point or mixed
  PRIMARY KEY (id)
);
CREATE TABLE stvds_base (
  id VARCHAR NOT NULL,                 -- Id of the space-time dataset, name@mapset this is the primary key
  name VARCHAR NOT NULL,               -- name of the space-time dataset
  mapset VARCHAR NOT NULL,             -- mapset of the space-time dataset
  creator VARCHAR NOT NULL,            -- Name of the creator
  temporal_type VARCHAR NOT NULL,      -- The temporal type of the dataset "absolute" or "relative"
  semantic_type VARCHAR NOT NULL,      -- The semantic data description used for aggregation/decomposition algorithm selection: min, max, mean or sum
  creation_time TIMESTAMP NOT NULL,    -- The time of creation of the space-time dataset
  modification_time TIMESTAMP NOT NULL,-- The time of the last modification of the space time dataset
  PRIMARY KEY (id)
);
CREATE TABLE stvds_metadata (
  id VARCHAR NOT NULL,    -- Name of the space-time vector dataset, this is the primary key
  vector_register VARCHAR,-- The id of the table in which the vector maps are registered for this dataset
  number_of_maps INTEGER, -- The number of registered vector maps
  title VARCHAR,          -- Title of the space-time vector dataset
  description VARCHAR,    -- Detailed description of the space-time vector dataset
  command VARCHAR,        -- The command that was used to create the space time vector dataset
  points INTEGER,         -- The number of points accumulated from all registered maps
  lines INTEGER,          -- The number of lines accumulated from all registered maps
  boundaries INTEGER,     -- The number of boundaries accumulated from all registered maps
  centroids INTEGER,      -- The number of centroids accumulated from all registered maps
  faces INTEGER,          -- The number of faces accumulated from all registered maps
  kernels INTEGER,        -- The number of kernels accumulated from all registered maps
  primitives INTEGER,     -- All primitives accumulated (points, lines,boundaries,centroids,faces,kernels)
  nodes INTEGER,          -- Number of nodes accumulated from all registered maps (topological information)
  areas INTEGER,          -- The number of areas accumulated from all registered maps (topological information)
  islands INTEGER,        -- The number of islands accumulated from all registered maps (topological information)
  holes INTEGER,          -- The number of holes accumulated from all registered maps (topological information)
  volumes INTEGER,        -- The number of volumes accumulated from all registered maps (topological information)           -- The command that was used to create the space time raster dataset
  PRIMARY KEY (id)
);
CREATE TABLE stvds_relative_time (
  id VARCHAR NOT NULL,            -- Id of the space-time dataset, this is the primary key
  start_time INTEGER,             -- The relative valid start time
  end_time INTEGER,               -- The relative valid end time
  granularity INTEGER,            -- The granularity
  unit VARCHAR,                   -- The relative time unit, available are "years, months, days, minutes, seconds"
  map_time VARCHAR,               -- The temporal type of the registered maps, may be interval, point or mixed
  PRIMARY KEY (id)
);
CREATE TABLE stvds_spatial_extent (
  id VARCHAR NOT NULL,      -- Id of the space-time dataset, this is the primary key
  north DOUBLE PRECISION,   -- The spatial north extent, derived from the registered maps
  south DOUBLE PRECISION,   -- The spatial south extent, derived from the registered maps
  east DOUBLE PRECISION,    -- The spatial east extent, derived from the registered maps
  west DOUBLE PRECISION,    -- The spatial west extent, derived from the registered maps
  top DOUBLE PRECISION,     -- The spatial top extent, derived from the registered maps
  bottom DOUBLE PRECISION,  -- The spatial bottom extent, derived from the registered maps
  proj VARCHAR,      -- The projection of the space time dataset (XY of LL)
  PRIMARY KEY (id)
);
CREATE TABLE tgis_metadata (key VARCHAR NOT NULL, value VARCHAR);
CREATE TABLE vector_absolute_time (
  id VARCHAR NOT NULL,   -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  start_time TIMESTAMP,  --  Start of the valid time, can be NULL if no time information is available
  end_time TIMESTAMP,    --  End of the valid time, can be NULL if no time information is available or valid time is a single point in time
  PRIMARY KEY (id)
);
CREATE TABLE vector_base (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name (layer) and mapset (name(:layer)@mapset) and is used as primary key
  name VARCHAR NOT NULL,                -- name of the grass map
  mapset VARCHAR NOT NULL,              -- mapset of the grass map
  layer VARCHAR,                        -- The layer id of the map, this is currently only in use by vector maps
  creator VARCHAR NOT NULL,
  temporal_type VARCHAR,                -- The temporal type of the grass map "absolute" or "relative" or NULL in case no time stamp is available
  creation_time TIMESTAMP NOT NULL,      -- The time of creation of the grass map
  PRIMARY KEY (id)
);
CREATE TABLE vector_map_register_46aab9946b1c5c16112d3e4b761007e7 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE vector_map_register_88f60c6d82d6b5d5a15b96d6d64da7d4 (
  id VARCHAR NOT NULL, -- This column is a primary key storing the registered GRASS_MAP map.ids
  PRIMARY KEY (id)
);
CREATE TABLE vector_metadata (
  id VARCHAR NOT NULL,    -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  is_3d BOOLEAN,          -- This is 1 if the vector map is 3d and 0 otherwise
  points INTEGER,         -- The number of points
  lines INTEGER,          -- The number of lines
  boundaries INTEGER,     -- The number of boundaries
  centroids INTEGER,      -- The number of centroids
  faces INTEGER,          -- The number of faces
  kernels INTEGER,        -- The number of kernels
  primitives INTEGER,     -- All primitives accumulated (points, lines,boundaries,centroids,faces,kernels)
  nodes INTEGER,          -- Number of nodes (topological information)
  areas INTEGER,          -- The number of areas (topological information)
  islands INTEGER,        -- The number of islands (topological information)
  holes INTEGER,          -- The number of holes (topological information)
  volumes INTEGER,        -- The number of volumes (topological information)
  PRIMARY KEY (id)
);
CREATE TABLE vector_relative_time (
  id VARCHAR NOT NULL,          -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary foreign key
  start_time INTEGER,  -- The relative valid start time in
  end_time INTEGER,    -- The relative valid end time in
  unit VARCHAR,                 -- The relative time unit, available are "years, months, days, minutes, seconds"
  PRIMARY KEY (id)
);
CREATE TABLE vector_spatial_extent (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name and mapset (name@mapset) and is used as primary key
  -- below is the spatial extent of the map
  north DOUBLE PRECISION NOT NULL,
  south DOUBLE PRECISION NOT NULL,
  east DOUBLE PRECISION NOT NULL,
  west DOUBLE PRECISION NOT NULL,
  top DOUBLE PRECISION NOT NULL,
  bottom DOUBLE PRECISION NOT NULL,
  proj VARCHAR,
  PRIMARY KEY (id)
);
CREATE TABLE vector_stds_register (
  id VARCHAR NOT NULL,                  -- The id (PK) is the unique identifier for all tables, it is based on name (layer) and mapset (name(:layer)@mapset) and is used as primary key
  registered_stds VARCHAR,              -- This column stores the names of all space time datasets in which a specific map is registered
  PRIMARY KEY (id)
);
CREATE INDEX raster3d_absolute_time_index ON raster3d_absolute_time (id, start_time, end_time);
CREATE INDEX raster3d_base_index ON raster3d_base (id);
CREATE INDEX raster3d_map_register_7f402c6f1a3eb2af4c63c569ee489d93_index ON raster3d_map_register_7f402c6f1a3eb2af4c63c569ee489d93 (id);
CREATE INDEX raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2_index ON raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2 (id);
CREATE INDEX raster3d_metadata_index ON raster3d_metadata (id);
CREATE INDEX raster3d_relative_time_index ON raster3d_relative_time (id, start_time, end_time);
CREATE INDEX raster3d_spatial_extent_index ON raster3d_spatial_extent (id);
CREATE INDEX raster3d_spatial_extent_index_bbox ON raster3d_spatial_extent (id, north, south, east, west, top, bottom);
CREATE INDEX raster3d_stds_register_index ON raster3d_stds_register (id);
CREATE INDEX raster_absolute_time_index ON raster_absolute_time (id, start_time, end_time);
CREATE INDEX raster_base_index ON raster_base (id);
CREATE INDEX raster_map_register_22e3c261135396136fb4632c4a1f5601_index ON raster_map_register_22e3c261135396136fb4632c4a1f5601 (id);
CREATE INDEX raster_map_register_61faa24dfaecfe07b7c99ea4666187c8_index ON raster_map_register_61faa24dfaecfe07b7c99ea4666187c8 (id);
CREATE INDEX raster_map_register_638463c28b29c46ee1ff78f2993f2bc1_index ON raster_map_register_638463c28b29c46ee1ff78f2993f2bc1 (id);
CREATE INDEX raster_map_register_a9894a19e40d453484aac2241aa57ab7_index ON raster_map_register_a9894a19e40d453484aac2241aa57ab7 (id);
CREATE INDEX raster_map_register_a9ad879a5ba0038ca0ea7257d239a0d1_index ON raster_map_register_a9ad879a5ba0038ca0ea7257d239a0d1 (id);
CREATE INDEX raster_map_register_f258237acb32c393a438f22c9634201b_index ON raster_map_register_f258237acb32c393a438f22c9634201b (id);
CREATE INDEX raster_metadata_index ON raster_metadata (id);
CREATE INDEX raster_metadata_index_semantic_label ON raster_metadata (id, semantic_label);
CREATE INDEX raster_relative_time_index ON raster_relative_time (id, start_time, end_time);
CREATE INDEX raster_spatial_extent_index ON raster_spatial_extent (id);
CREATE INDEX raster_spatial_extent_index_bbox ON raster_spatial_extent (id, north, south, east, west);
CREATE INDEX raster_stds_register_index ON raster_stds_register (id);
CREATE INDEX str3ds_absolute_time_index ON str3ds_absolute_time (id);
CREATE INDEX str3ds_base_index ON str3ds_base (id);
CREATE INDEX str3ds_metadata_index ON str3ds_metadata (id);
CREATE INDEX str3ds_relative_time_index ON str3ds_relative_time (id);
CREATE INDEX str3ds_spatial_extent_index ON str3ds_spatial_extent (id);
CREATE INDEX strds_absolute_time_index ON strds_absolute_time (id);
CREATE INDEX strds_base_index ON strds_base (id);
CREATE INDEX strds_metadata_index ON strds_metadata (id);
CREATE INDEX strds_relative_time_index ON strds_relative_time (id);
CREATE INDEX strds_spatial_extent_index ON strds_spatial_extent (id);
CREATE INDEX stvds_absolute_time_index ON stvds_absolute_time (id);
CREATE INDEX stvds_base_index ON stvds_base (id);
CREATE INDEX stvds_metadata_index ON stvds_metadata (id);
CREATE INDEX stvds_relative_time_index ON stvds_relative_time (id);
CREATE INDEX stvds_spatial_extent_index ON stvds_spatial_extent (id);
CREATE INDEX vector_absolute_time_index ON vector_absolute_time (id, start_time, end_time);
CREATE INDEX vector_base_index ON vector_base (id);
CREATE INDEX vector_map_register_46aab9946b1c5c16112d3e4b761007e7_index ON vector_map_register_46aab9946b1c5c16112d3e4b761007e7 (id);
CREATE INDEX vector_map_register_88f60c6d82d6b5d5a15b96d6d64da7d4_index ON vector_map_register_88f60c6d82d6b5d5a15b96d6d64da7d4 (id);
CREATE INDEX vector_metadata_index ON vector_metadata (id);
CREATE INDEX vector_relative_time_index ON vector_relative_time (id, start_time, end_time);
CREATE INDEX vector_spatial_extent_index ON vector_spatial_extent (id);
CREATE INDEX vector_spatial_extent_index_bbox ON vector_spatial_extent (id, north, south, east, west, top, bottom);
CREATE INDEX vector_stds_register_index ON vector_stds_register (id);
CREATE VIEW raster3d_view_abs_time AS SELECT
            A1.id, A1.mapset,
            A1.name, A1.temporal_type,
            A1.creation_time,
            A1.creator,
            A2.start_time, A2.end_time,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.datatype, A4.cols, A4.rows, A4.depths,
            A4.nsres, A4.ewres, A4.tbres,
            A4.min, A4.max,
            A4.number_of_cells, A5.registered_stds
            FROM raster3d_base A1, raster3d_absolute_time A2,
            raster3d_spatial_extent A3, raster3d_metadata A4,
            raster3d_stds_register A5
            WHERE A1.id = A2.id AND A1.id = A3.id AND
            A1.id = A4.id AND A1.id = A5.id;
CREATE VIEW raster3d_view_rel_time AS SELECT
            A1.id, A1.mapset,
            A1.name, A1.temporal_type,
            A1.creation_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.unit,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.datatype, A4.cols, A4.rows, A4.depths,
            A4.nsres, A4.ewres, A4.tbres,
            A4.min, A4.max,
            A4.number_of_cells, A5.registered_stds
            FROM raster3d_base A1, raster3d_relative_time A2,
            raster3d_spatial_extent A3, raster3d_metadata A4,
            raster3d_stds_register A5
            WHERE A1.id = A2.id AND A1.id = A3.id AND
            A1.id = A4.id AND A1.id = A5.id;
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
CREATE VIEW strds_view_abs_time AS SELECT
            A1.id, A1.name, A1.mapset, A1.temporal_type,
            A1.semantic_type,
            A1.creation_time, A1.modification_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.granularity,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.raster_register,
            A4.number_of_maps,
            A4.nsres_min, A4.ewres_min,
            A4.nsres_max, A4.ewres_max,
            A4.min_min, A4.min_max,
            A4.max_min, A4.max_max, A4.aggregation_type,
            A4.title, A4.description, A4.command
            FROM strds_base A1, strds_absolute_time A2,
            strds_spatial_extent A3, strds_metadata A4 WHERE A1.id = A2.id AND
            A1.id = A3.id AND A1.id = A4.id;
CREATE VIEW strds_view_rel_time AS SELECT
            A1.id, A1.name, A1.mapset, A1.temporal_type,
            A1.semantic_type,
            A1.creation_time, A1.modification_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.unit, A2.granularity,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.raster_register,
            A4.number_of_maps,
            A4.nsres_min, A4.ewres_min,
            A4.nsres_max, A4.ewres_max,
            A4.min_min, A4.min_max,
            A4.max_min, A4.max_max, A4.aggregation_type,
            A4.title, A4.description, A4.command
            FROM strds_base A1, strds_relative_time A2,
            strds_spatial_extent A3, strds_metadata A4 WHERE A1.id = A2.id AND
            A1.id = A3.id AND A1.id = A4.id;
CREATE VIEW stvds_view_abs_time AS SELECT
            A1.id, A1.name, A1.mapset, A1.temporal_type,
            A1.semantic_type,
            A1.creation_time, A1.modification_time,
            A1.creator,
            A2.start_time, A2.end_time,
            A2.granularity,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.vector_register,
            A4.number_of_maps,
            A4.title, A4.description, A4.command, A4.points, A4.lines,
            A4.boundaries, A4.centroids, A4.faces, A4.kernels,
            A4.primitives, A4.nodes, A4.areas, A4.islands,
            A4.holes, A4.volumes
            FROM stvds_base A1, stvds_absolute_time A2,
            stvds_spatial_extent A3, stvds_metadata A4 WHERE A1.id = A2.id AND
            A1.id = A3.id AND A1.id = A4.id;
CREATE VIEW stvds_view_rel_time AS SELECT
            A1.id, A1.name, A1.mapset, A1.temporal_type,
            A1.semantic_type,
            A1.creation_time, A1.modification_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.unit, A2.granularity,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.vector_register,
            A4.number_of_maps,
            A4.title, A4.description, A4.command, A4.points, A4.lines,
            A4.boundaries, A4.centroids, A4.faces, A4.kernels,
            A4.primitives, A4.nodes, A4.areas, A4.islands,
            A4.holes, A4.volumes
            FROM stvds_base A1, stvds_relative_time A2,
            stvds_spatial_extent A3, stvds_metadata A4 WHERE A1.id = A2.id AND
            A1.id = A3.id AND A1.id = A4.id;
CREATE VIEW vector_view_abs_time AS SELECT
            A1.id, A1.mapset,
            A1.name, A1.layer, A1.temporal_type,
            A1.creation_time,
            A1.creator,
            A2.start_time, A2.end_time,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.is_3d, A4.points, A4.lines,
            A4.boundaries, A4.centroids, A4.faces, A4.kernels,
            A4.primitives, A4.nodes, A4.areas, A4.islands,
            A4.holes, A4.volumes, A5.registered_stds
            FROM vector_base A1, vector_absolute_time A2,
            vector_spatial_extent A3, vector_metadata A4,
            vector_stds_register A5
            WHERE A1.id = A2.id AND A1.id = A3.id AND
            A1.id = A4.id AND A1.id = A5.id;
CREATE VIEW vector_view_rel_time AS SELECT
            A1.id, A1.mapset,
            A1.name, A1.layer, A1.temporal_type,
            A1.creation_time,
            A1.creator,
            A2.start_time, A2.end_time, A2.unit,
            A3.north, A3.south, A3.east, A3.west, A3.bottom, A3.top, A3.proj,
            A4.is_3d, A4.points, A4.lines,
            A4.boundaries, A4.centroids, A4.faces, A4.kernels,
            A4.primitives, A4.nodes, A4.areas, A4.islands,
            A4.holes, A4.volumes, A5.registered_stds
            FROM vector_base A1, vector_relative_time A2,
            vector_spatial_extent A3, vector_metadata A4,
            vector_stds_register A5
            WHERE A1.id = A2.id AND A1.id = A3.id AND
            A1.id = A4.id AND A1.id = A5.id;
CREATE TRIGGER delete_raster3d_base AFTER DELETE ON raster3d_base
  BEGIN
    DELETE FROM raster3d_absolute_time WHERE id = old.id;
    DELETE FROM raster3d_relative_time WHERE id = old.id;
    DELETE FROM raster3d_spatial_extent WHERE id = old.id;
    DELETE FROM raster3d_metadata WHERE id = old.id;
    DELETE FROM raster3d_stds_register WHERE id = old.id;
  END;
CREATE TRIGGER delete_raster_base AFTER DELETE ON raster_base
  BEGIN
    DELETE FROM raster_absolute_time WHERE id = old.id;
    DELETE FROM raster_relative_time WHERE id = old.id;
    DELETE FROM raster_spatial_extent WHERE id = old.id;
    DELETE FROM raster_metadata WHERE id = old.id;
    DELETE FROM raster_stds_register WHERE id = old.id;
  END;
CREATE TRIGGER delete_str3ds_base AFTER DELETE ON str3ds_base
  BEGIN
    DELETE FROM str3ds_absolute_time WHERE id = old.id;
    DELETE FROM str3ds_relative_time WHERE id = old.id;
    DELETE FROM str3ds_spatial_extent WHERE id = old.id;
    DELETE FROM str3ds_metadata WHERE id = old.id;
  END;
CREATE TRIGGER delete_strds_base AFTER DELETE ON strds_base
  BEGIN
    DELETE FROM strds_absolute_time WHERE id = old.id;
    DELETE FROM strds_relative_time WHERE id = old.id;
    DELETE FROM strds_spatial_extent WHERE id = old.id;
    DELETE FROM strds_metadata WHERE id = old.id;
  END;
CREATE TRIGGER delete_stvds_base AFTER DELETE ON stvds_base
  BEGIN
    DELETE FROM stvds_absolute_time WHERE id = old.id;
    DELETE FROM stvds_relative_time WHERE id = old.id;
    DELETE FROM stvds_spatial_extent WHERE id = old.id;
    DELETE FROM stvds_metadata WHERE id = old.id;
  END;
CREATE TRIGGER delete_vector_base AFTER DELETE ON vector_base
  BEGIN
    DELETE FROM vector_absolute_time WHERE id = old.id;
    DELETE FROM vector_relative_time WHERE id = old.id;
    DELETE FROM vector_spatial_extent WHERE id = old.id;
    DELETE FROM vector_metadata WHERE id = old.id;
    DELETE FROM vector_stds_register WHERE id = old.id;
  END;
INSERT INTO "raster3d_absolute_time" VALUES('gone_1@PERMANENT','2001-01-01 00:00:00','2001-01-03 00:00:00');
INSERT INTO "raster3d_absolute_time" VALUES('vol_1@PERMANENT','2001-02-02 00:00:00','2001-02-03 00:00:00');
INSERT INTO "raster3d_absolute_time" VALUES('vol_2@PERMANENT','2001-02-03 00:00:00','2001-02-04 00:00:00');
INSERT INTO "raster3d_absolute_time" VALUES('vol_3@PERMANENT','2001-02-04 00:00:00','2001-02-05 00:00:00');
INSERT INTO "raster3d_base" VALUES('gone_1@PERMANENT','gone_1','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster3d_base" VALUES('rvol_1@PERMANENT','rvol_1','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster3d_base" VALUES('rvol_2@PERMANENT','rvol_2','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster3d_base" VALUES('vol_1@PERMANENT','vol_1','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster3d_base" VALUES('vol_2@PERMANENT','vol_2','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster3d_base" VALUES('vol_3@PERMANENT','vol_3','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster3d_map_register_7f402c6f1a3eb2af4c63c569ee489d93" VALUES('rvol_1@PERMANENT');
INSERT INTO "raster3d_map_register_7f402c6f1a3eb2af4c63c569ee489d93" VALUES('rvol_2@PERMANENT');
INSERT INTO "raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2" VALUES('vol_1@PERMANENT');
INSERT INTO "raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2" VALUES('vol_2@PERMANENT');
INSERT INTO "raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2" VALUES('vol_3@PERMANENT');
INSERT INTO "raster3d_metadata" VALUES('gone_1@PERMANENT','DCELL',1,1,1,1,1.0,1.0,1.0,1.0,1.0);
INSERT INTO "raster3d_metadata" VALUES('rvol_1@PERMANENT','DCELL',1,1,1,1,1.0,1.0,1.0,1.0,1.0);
INSERT INTO "raster3d_metadata" VALUES('rvol_2@PERMANENT','DCELL',1,1,1,1,1.0,1.0,1.0,2.0,2.0);
INSERT INTO "raster3d_metadata" VALUES('vol_1@PERMANENT','DCELL',1,1,1,1,1.0,1.0,1.0,1.0,1.0);
INSERT INTO "raster3d_metadata" VALUES('vol_2@PERMANENT','DCELL',1,1,1,1,1.0,1.0,1.0,2.0,2.0);
INSERT INTO "raster3d_metadata" VALUES('vol_3@PERMANENT','DCELL',1,1,1,1,1.0,1.0,1.0,3.0,3.0);
INSERT INTO "raster3d_relative_time" VALUES('rvol_1@PERMANENT',1,3,'years');
INSERT INTO "raster3d_relative_time" VALUES('rvol_2@PERMANENT',2,4,'years');
INSERT INTO "raster3d_spatial_extent" VALUES('gone_1@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "raster3d_spatial_extent" VALUES('rvol_1@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "raster3d_spatial_extent" VALUES('rvol_2@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "raster3d_spatial_extent" VALUES('vol_1@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "raster3d_spatial_extent" VALUES('vol_2@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "raster3d_spatial_extent" VALUES('vol_3@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "raster3d_stds_register" VALUES('gone_1@PERMANENT','');
INSERT INTO "raster3d_stds_register" VALUES('rvol_1@PERMANENT','rel_raster3d@PERMANENT');
INSERT INTO "raster3d_stds_register" VALUES('rvol_2@PERMANENT','rel_raster3d@PERMANENT');
INSERT INTO "raster3d_stds_register" VALUES('vol_1@PERMANENT','abs_raster3d@PERMANENT');
INSERT INTO "raster3d_stds_register" VALUES('vol_2@PERMANENT','abs_raster3d@PERMANENT');
INSERT INTO "raster3d_stds_register" VALUES('vol_3@PERMANENT','abs_raster3d@PERMANENT');
INSERT INTO "raster_absolute_time" VALUES('img_1@PERMANENT','2001-01-01 00:00:00','2001-02-01 00:00:00');
INSERT INTO "raster_absolute_time" VALUES('img_2@PERMANENT','2001-02-01 00:00:00','2001-03-01 00:00:00');
INSERT INTO "raster_absolute_time" VALUES('img_3@PERMANENT','2001-03-01 00:00:00','2001-04-11 00:00:00');
INSERT INTO "raster_absolute_time" VALUES('img_4@PERMANENT','2001-04-11 00:00:00','2001-05-01 00:00:00');
INSERT INTO "raster_absolute_time" VALUES('lib_1@PERMANENT','2001-01-03 00:00:00','2001-01-08 00:00:00');
INSERT INTO "raster_absolute_time" VALUES('lib_2@PERMANENT','2001-01-08 00:00:00','2001-01-12 00:00:00');
INSERT INTO "raster_base" VALUES('img_1@PERMANENT','img_1','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('img_2@PERMANENT','img_2','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('img_3@PERMANENT','img_3','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('img_4@PERMANENT','img_4','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('lib_1@PERMANENT','lib_1','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('lib_2@PERMANENT','lib_2','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('lib_3@PERMANENT','lib_3','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('lib_4@PERMANENT','lib_4','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('rel_1@PERMANENT','rel_1','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('rel_2@PERMANENT','rel_2','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster_base" VALUES('rel_3@PERMANENT','rel_3','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "raster_map_register_22e3c261135396136fb4632c4a1f5601" VALUES('img_1@PERMANENT');
INSERT INTO "raster_map_register_22e3c261135396136fb4632c4a1f5601" VALUES('img_2@PERMANENT');
INSERT INTO "raster_map_register_22e3c261135396136fb4632c4a1f5601" VALUES('img_3@PERMANENT');
INSERT INTO "raster_map_register_22e3c261135396136fb4632c4a1f5601" VALUES('img_4@PERMANENT');
INSERT INTO "raster_map_register_61faa24dfaecfe07b7c99ea4666187c8" VALUES('rel_1@PERMANENT');
INSERT INTO "raster_map_register_61faa24dfaecfe07b7c99ea4666187c8" VALUES('rel_2@PERMANENT');
INSERT INTO "raster_map_register_61faa24dfaecfe07b7c99ea4666187c8" VALUES('rel_3@PERMANENT');
INSERT INTO "raster_map_register_638463c28b29c46ee1ff78f2993f2bc1" VALUES('img_1@PERMANENT');
INSERT INTO "raster_map_register_638463c28b29c46ee1ff78f2993f2bc1" VALUES('img_2@PERMANENT');
INSERT INTO "raster_map_register_638463c28b29c46ee1ff78f2993f2bc1" VALUES('img_3@PERMANENT');
INSERT INTO "raster_map_register_a9894a19e40d453484aac2241aa57ab7" VALUES('img_1@PERMANENT');
INSERT INTO "raster_map_register_a9894a19e40d453484aac2241aa57ab7" VALUES('img_2@PERMANENT');
INSERT INTO "raster_map_register_a9894a19e40d453484aac2241aa57ab7" VALUES('img_3@PERMANENT');
INSERT INTO "raster_map_register_a9894a19e40d453484aac2241aa57ab7" VALUES('img_4@PERMANENT');
INSERT INTO "raster_map_register_a9894a19e40d453484aac2241aa57ab7" VALUES('lib_1@PERMANENT');
INSERT INTO "raster_map_register_a9894a19e40d453484aac2241aa57ab7" VALUES('lib_2@PERMANENT');
INSERT INTO "raster_map_register_a9ad879a5ba0038ca0ea7257d239a0d1" VALUES('lib_3@PERMANENT');
INSERT INTO "raster_map_register_a9ad879a5ba0038ca0ea7257d239a0d1" VALUES('lib_4@PERMANENT');
INSERT INTO "raster_map_register_f258237acb32c393a438f22c9634201b" VALUES('lib_1@PERMANENT');
INSERT INTO "raster_map_register_f258237acb32c393a438f22c9634201b" VALUES('lib_2@PERMANENT');
INSERT INTO "raster_metadata" VALUES('img_1@PERMANENT','CELL',1,1,1,1.0,1.0,1.0,1.0,'S2_1');
INSERT INTO "raster_metadata" VALUES('img_2@PERMANENT','CELL',1,1,1,1.0,1.0,2.0,2.0,'S2_1');
INSERT INTO "raster_metadata" VALUES('img_3@PERMANENT','CELL',1,1,1,1.0,1.0,3.0,3.0,'S2_2');
INSERT INTO "raster_metadata" VALUES('img_4@PERMANENT','CELL',1,1,1,1.0,1.0,4.0,4.0,'S2_3');
INSERT INTO "raster_metadata" VALUES('lib_1@PERMANENT','CELL',1,1,1,1.0,1.0,1.0,1.0,NULL);
INSERT INTO "raster_metadata" VALUES('lib_2@PERMANENT','CELL',1,1,1,1.0,1.0,1.0,1.0,NULL);
INSERT INTO "raster_metadata" VALUES('lib_3@PERMANENT','CELL',1,1,1,1.0,1.0,1.0,1.0,NULL);
INSERT INTO "raster_metadata" VALUES('lib_4@PERMANENT','CELL',1,1,1,1.0,1.0,1.0,1.0,NULL);
INSERT INTO "raster_metadata" VALUES('rel_1@PERMANENT','CELL',1,1,1,1.0,1.0,1.0,1.0,NULL);
INSERT INTO "raster_metadata" VALUES('rel_2@PERMANENT','CELL',1,1,1,1.0,1.0,2.0,2.0,NULL);
INSERT INTO "raster_metadata" VALUES('rel_3@PERMANENT','CELL',1,1,1,1.0,1.0,3.0,3.0,NULL);
INSERT INTO "raster_relative_time" VALUES('lib_3@PERMANENT',0,4,'days');
INSERT INTO "raster_relative_time" VALUES('lib_4@PERMANENT',4,9,'days');
INSERT INTO "raster_relative_time" VALUES('rel_1@PERMANENT',15,25,'days');
INSERT INTO "raster_relative_time" VALUES('rel_2@PERMANENT',25,35,'days');
INSERT INTO "raster_relative_time" VALUES('rel_3@PERMANENT',35,45,'days');
INSERT INTO "raster_spatial_extent" VALUES('img_1@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('img_2@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('img_3@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('img_4@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('lib_1@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('lib_2@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('lib_3@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('lib_4@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('rel_1@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('rel_2@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_spatial_extent" VALUES('rel_3@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "raster_stds_register" VALUES('img_1@PERMANENT','abs_raster@PERMANENT,copied@PERMANENT,merged@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('img_2@PERMANENT','abs_raster@PERMANENT,copied@PERMANENT,merged@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('img_3@PERMANENT','abs_raster@PERMANENT,copied@PERMANENT,merged@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('img_4@PERMANENT','copied@PERMANENT,merged@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('lib_1@PERMANENT','lib_abs@PERMANENT,merged@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('lib_2@PERMANENT','lib_abs@PERMANENT,merged@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('lib_3@PERMANENT','renamed_rel@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('lib_4@PERMANENT','renamed_rel@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('rel_1@PERMANENT','rel_raster@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('rel_2@PERMANENT','rel_raster@PERMANENT');
INSERT INTO "raster_stds_register" VALUES('rel_3@PERMANENT','rel_raster@PERMANENT');
INSERT INTO "str3ds_absolute_time" VALUES('abs_raster3d@PERMANENT','2001-02-02 00:00:00','2001-02-05 00:00:00','1 day','interval');
INSERT INTO "str3ds_base" VALUES('abs_raster3d@PERMANENT','abs_raster3d','PERMANENT','user','absolute','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "str3ds_base" VALUES('rel_raster3d@PERMANENT','rel_raster3d','PERMANENT','user','relative','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "str3ds_metadata" VALUES('abs_raster3d@PERMANENT','raster3d_map_register_ba841f5ed408aa3b1114defc53dc2ff2',3,1.0,1.0,3.0,3.0,1.0,1.0,1.0,1.0,1.0,1.0,NULL,'Absolute 3D raster','Absolute 3D raster','# TIME 
t.create type="str3ds" output="abs_raster3d"
    temporaltype="absolute" title="Absolute 3D raster"
    description="Absolute 3D raster"
# TIME 
t.register type="raster_3d" input="abs_raster3d"
    file="TMPDIR/maps.txt"
# TIME 
t.support -m input="abs_raster3d" type="str3ds"
# TIME 
t.shift input="abs_raster3d" type="str3ds"
    granularity="1 month"
');
INSERT INTO "str3ds_metadata" VALUES('rel_raster3d@PERMANENT','raster3d_map_register_7f402c6f1a3eb2af4c63c569ee489d93',2,1.0,1.0,2.0,2.0,1.0,1.0,1.0,1.0,1.0,1.0,NULL,'rel_raster3d','rel_raster3d','# TIME 
t.create type="str3ds" output="rel_raster3d"
    temporaltype="relative" title="rel_raster3d" description="rel_raster3d"
# TIME 
t.register type="raster_3d" input="rel_raster3d"
    file="TMPDIR/maps.txt" unit="years"
');
INSERT INTO "str3ds_relative_time" VALUES('rel_raster3d@PERMANENT',1,4,2,'years','interval');
INSERT INTO "str3ds_spatial_extent" VALUES('abs_raster3d@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "str3ds_spatial_extent" VALUES('rel_raster3d@PERMANENT',1.0,0.0,1.0,0.0,1.0,0.0,'XY');
INSERT INTO "strds_absolute_time" VALUES('abs_raster@PERMANENT','2001-01-01 00:00:00','2001-04-11 00:00:00','1 day','interval');
INSERT INTO "strds_absolute_time" VALUES('copied@PERMANENT','2001-01-01 00:00:00','2001-05-01 00:00:00','1 day','interval');
INSERT INTO "strds_absolute_time" VALUES('lib_abs@PERMANENT','2001-01-03 00:00:00','2001-01-12 00:00:00','1 day','interval');
INSERT INTO "strds_absolute_time" VALUES('merged@PERMANENT','2001-01-01 00:00:00','2001-05-01 00:00:00','1 day','interval');
INSERT INTO "strds_base" VALUES('abs_raster@PERMANENT','abs_raster','PERMANENT','user','absolute','max','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "strds_base" VALUES('copied@PERMANENT','copied','PERMANENT','user','absolute','max','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "strds_base" VALUES('lib_abs@PERMANENT','lib_abs','PERMANENT','user','absolute','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "strds_base" VALUES('merged@PERMANENT','merged','PERMANENT','user','absolute','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "strds_base" VALUES('rel_raster@PERMANENT','rel_raster','PERMANENT','user','relative','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "strds_base" VALUES('renamed_rel@PERMANENT','renamed_rel','PERMANENT','user','relative','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "strds_metadata" VALUES('abs_raster@PERMANENT','raster_map_register_638463c28b29c46ee1ff78f2993f2bc1',3,1.0,1.0,3.0,3.0,1.0,1.0,1.0,1.0,NULL,2,'Changed title','Changed description','# TIME 
t.create type="strds" output="abs_raster"
    temporaltype="absolute" title="Absolute raster"
    description="Absolute raster"
# TIME 
t.register type="raster" input="abs_raster"
    file="TMPDIR/maps.txt"
# TIME 
t.support -m input="abs_raster" type="strds"
    title="Changed title" description="Changed description"
    semantictype="max"
# TIME 
t.support -m input="abs_raster" type="strds"
# TIME 
t.snap input="abs_raster" type="strds"
# TIME 
t.unregister type="raster" input="abs_raster"
    file="TMPDIR/maps.txt"
');
INSERT INTO "strds_metadata" VALUES('copied@PERMANENT','raster_map_register_22e3c261135396136fb4632c4a1f5601',4,1.0,1.0,4.0,4.0,1.0,1.0,1.0,1.0,NULL,3,'Changed title','Changed description','# TIME 
t.copy input="abs_raster" output="copied"
    type="strds"
');
INSERT INTO "strds_metadata" VALUES('lib_abs@PERMANENT','raster_map_register_f258237acb32c393a438f22c9634201b',2,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,NULL,0,'lib_abs','lib_abs','# TIME 
scenario
# TIME 
scenario
# TIME 
scenario
# TIME 
t.shift input="lib_abs" type="strds"
    granularity="2 days"
');
INSERT INTO "strds_metadata" VALUES('merged@PERMANENT','raster_map_register_a9894a19e40d453484aac2241aa57ab7',6,1.0,1.0,4.0,4.0,1.0,1.0,1.0,1.0,NULL,3,'Merged space time dataset','Merged space time dataset','# TIME 
t.merge input="abs_raster,lib_abs" output="merged"
    type="strds"
');
INSERT INTO "strds_metadata" VALUES('rel_raster@PERMANENT','raster_map_register_61faa24dfaecfe07b7c99ea4666187c8',3,1.0,1.0,3.0,3.0,1.0,1.0,1.0,1.0,NULL,0,'Relative raster','Relative raster','# TIME 
t.create type="strds" output="rel_raster"
    temporaltype="relative" title="Relative raster"
    description="Relative raster"
# TIME 
t.register type="raster" input="rel_raster"
    file="TMPDIR/maps.txt" unit="days"
# TIME 
t.shift input="rel_raster" type="strds"
    granularity="5"
# TIME 
t.snap input="rel_raster" type="strds"
');
INSERT INTO "strds_metadata" VALUES('renamed_rel@PERMANENT','raster_map_register_a9ad879a5ba0038ca0ea7257d239a0d1',2,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,NULL,0,'lib_rel','lib_rel','# TIME 
scenario
# TIME 
scenario
# TIME 
scenario
# TIME 
t.rename input="lib_rel" output="renamed_rel"
    type="strds"
');
INSERT INTO "strds_relative_time" VALUES('rel_raster@PERMANENT',15,45,10,'days','interval');
INSERT INTO "strds_relative_time" VALUES('renamed_rel@PERMANENT',0,9,1,'days','interval');
INSERT INTO "strds_spatial_extent" VALUES('abs_raster@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "strds_spatial_extent" VALUES('copied@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "strds_spatial_extent" VALUES('lib_abs@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "strds_spatial_extent" VALUES('merged@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "strds_spatial_extent" VALUES('rel_raster@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "strds_spatial_extent" VALUES('renamed_rel@PERMANENT',1.0,0.0,1.0,0.0,0.0,0.0,'XY');
INSERT INTO "stvds_absolute_time" VALUES('abs_vector@PERMANENT','2001-01-01 00:00:00','2001-01-31 00:00:00','10 days','interval');
INSERT INTO "stvds_base" VALUES('abs_vector@PERMANENT','abs_vector','PERMANENT','user','absolute','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "stvds_base" VALUES('rel_vector@PERMANENT','rel_vector','PERMANENT','user','relative','mean','2000-01-01 00:00:00','2000-01-01 00:00:00');
INSERT INTO "stvds_metadata" VALUES('abs_vector@PERMANENT','vector_map_register_46aab9946b1c5c16112d3e4b761007e7',3,'abs_vector','abs_vector','# TIME 
t.create type="stvds" output="abs_vector"
    temporaltype="absolute" title="abs_vector" description="abs_vector"
# TIME 
t.register type="vector" input="abs_vector"
    file="TMPDIR/maps.txt"
# TIME 
t.support -m input="abs_vector" type="stvds"
# TIME 
t.unregister type="vector" input="abs_vector"
    maps="pts_b"
',5,0,0,0,0,0,5,0,0,0,0,0);
INSERT INTO "stvds_metadata" VALUES('rel_vector@PERMANENT','vector_map_register_88f60c6d82d6b5d5a15b96d6d64da7d4',2,'rel_vector','rel_vector','# TIME 
t.create type="stvds" output="rel_vector"
    temporaltype="relative" title="rel_vector" description="rel_vector"
# TIME 
t.register type="vector" input="rel_vector"
    file="TMPDIR/maps.txt" unit="months"
',2,0,0,0,0,0,2,0,0,0,0,0);
INSERT INTO "stvds_relative_time" VALUES('rel_vector@PERMANENT',1,8,1,'months','interval');
INSERT INTO "stvds_spatial_extent" VALUES('abs_vector@PERMANENT',3.0,0.2,3.0,0.2,0.0,0.0,'XY');
INSERT INTO "stvds_spatial_extent" VALUES('rel_vector@PERMANENT',5.0,4.0,5.0,4.0,0.0,0.0,'XY');
INSERT INTO "tgis_metadata" VALUES('creation_time','2000-01-01 00:00:00');
INSERT INTO "tgis_metadata" VALUES('tgis_db_version','3');
INSERT INTO "tgis_metadata" VALUES('tgis_version','2');
INSERT INTO "vector_absolute_time" VALUES('pts_a:2@PERMANENT','2001-01-01 00:00:00','2001-01-11 00:00:00');
INSERT INTO "vector_absolute_time" VALUES('pts_a@PERMANENT','2001-01-01 00:00:00','2001-01-11 00:00:00');
INSERT INTO "vector_absolute_time" VALUES('pts_b@PERMANENT','2001-01-11 00:00:00',NULL);
INSERT INTO "vector_absolute_time" VALUES('pts_c@PERMANENT','2001-01-21 00:00:00','2001-01-31 00:00:00');
INSERT INTO "vector_base" VALUES('pts_a:2@PERMANENT','pts_a','PERMANENT','2','user','absolute','2000-01-01 00:00:00');
INSERT INTO "vector_base" VALUES('pts_a@PERMANENT','pts_a','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "vector_base" VALUES('pts_b@PERMANENT','pts_b','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "vector_base" VALUES('pts_c@PERMANENT','pts_c','PERMANENT',NULL,'user','absolute','2000-01-01 00:00:00');
INSERT INTO "vector_base" VALUES('pts_d@PERMANENT','pts_d','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "vector_base" VALUES('pts_e@PERMANENT','pts_e','PERMANENT',NULL,'user','relative','2000-01-01 00:00:00');
INSERT INTO "vector_map_register_46aab9946b1c5c16112d3e4b761007e7" VALUES('pts_a:2@PERMANENT');
INSERT INTO "vector_map_register_46aab9946b1c5c16112d3e4b761007e7" VALUES('pts_a@PERMANENT');
INSERT INTO "vector_map_register_46aab9946b1c5c16112d3e4b761007e7" VALUES('pts_c@PERMANENT');
INSERT INTO "vector_map_register_88f60c6d82d6b5d5a15b96d6d64da7d4" VALUES('pts_d@PERMANENT');
INSERT INTO "vector_map_register_88f60c6d82d6b5d5a15b96d6d64da7d4" VALUES('pts_e@PERMANENT');
INSERT INTO "vector_metadata" VALUES('pts_a:2@PERMANENT',0,2,0,0,0,0,0,2,0,0,0,0,0);
INSERT INTO "vector_metadata" VALUES('pts_a@PERMANENT',0,2,0,0,0,0,0,2,0,0,0,0,0);
INSERT INTO "vector_metadata" VALUES('pts_b@PERMANENT',0,1,0,0,0,0,0,1,0,0,0,0,0);
INSERT INTO "vector_metadata" VALUES('pts_c@PERMANENT',0,1,0,0,0,0,0,1,0,0,0,0,0);
INSERT INTO "vector_metadata" VALUES('pts_d@PERMANENT',0,1,0,0,0,0,0,1,0,0,0,0,0);
INSERT INTO "vector_metadata" VALUES('pts_e@PERMANENT',0,1,0,0,0,0,0,1,0,0,0,0,0);
INSERT INTO "vector_relative_time" VALUES('pts_d@PERMANENT',1,3,'months');
INSERT INTO "vector_relative_time" VALUES('pts_e@PERMANENT',3,8,'months');
INSERT INTO "vector_spatial_extent" VALUES('pts_a:2@PERMANENT',0.5,0.2,0.5,0.2,0.0,0.0,'XY');
INSERT INTO "vector_spatial_extent" VALUES('pts_a@PERMANENT',0.5,0.2,0.5,0.2,0.0,0.0,'XY');
INSERT INTO "vector_spatial_extent" VALUES('pts_b@PERMANENT',2.0,2.0,2.0,2.0,0.0,0.0,'XY');
INSERT INTO "vector_spatial_extent" VALUES('pts_c@PERMANENT',3.0,3.0,3.0,3.0,0.0,0.0,'XY');
INSERT INTO "vector_spatial_extent" VALUES('pts_d@PERMANENT',4.0,4.0,4.0,4.0,0.0,0.0,'XY');
INSERT INTO "vector_spatial_extent" VALUES('pts_e@PERMANENT',5.0,5.0,5.0,5.0,0.0,0.0,'XY');
INSERT INTO "vector_stds_register" VALUES('pts_a:2@PERMANENT','abs_vector@PERMANENT');
INSERT INTO "vector_stds_register" VALUES('pts_a@PERMANENT','abs_vector@PERMANENT');
INSERT INTO "vector_stds_register" VALUES('pts_b@PERMANENT','');
INSERT INTO "vector_stds_register" VALUES('pts_c@PERMANENT','abs_vector@PERMANENT');
INSERT INTO "vector_stds_register" VALUES('pts_d@PERMANENT','rel_vector@PERMANENT');
INSERT INTO "vector_stds_register" VALUES('pts_e@PERMANENT','rel_vector@PERMANENT');
