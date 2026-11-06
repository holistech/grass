"""Find where and when the two field crews of tracks.py met

Each GPS position becomes a vector map object without a map: its time stamp
is the time of the position, its spatial extent the position. Snapping makes
each position last until the next one; buffering widens it by half the
distance to the next position, at least by 50 m. The topology builder then
relates the positions of the two crews in space and time.
"""

import csv
import math
from datetime import datetime

import grass.temporal as tgis

# The relations under which two positions share space and time
SPATIAL = ("EQUIVALENT", "COVER", "COVERED", "OVERLAP", "IN", "CONTAIN")
TEMPORAL = ("EQUAL", "DURING", "CONTAINS", "OVERLAPS", "OVERLAPPED")


def read_track(filename):
    """One VectorDataset object without a map for each position of a file"""
    positions = []
    with open(filename, newline="") as track:
        for east, north, time in csv.reader(track):
            position = tgis.VectorDataset(None)
            position.set_absolute_time(datetime.fromisoformat(time), None)
            position.set_spatial_extent_from_values(
                north=float(north),
                south=float(north),
                east=float(east),
                west=float(east),
                top=0,
                bottom=0,
            )
            positions.append(position)
    return positions


def buffer_positions(positions):
    """Widen each position by half the distance to the next one, at least 50 m"""
    for position, following in zip(positions, positions[1:] + [None], strict=True):
        distance = 0
        if following is not None:
            north, _south, east, *_rest = (
                position.spatial_extent.get_spatial_extent_as_tuple()
            )
            next_north, _south, next_east, *_rest = (
                following.spatial_extent.get_spatial_extent_as_tuple()
            )
            distance = math.hypot(next_east - east, next_north - north)
        position.spatial_buffer_2d(max(distance / 2, 50))


def temporal_relation(position, other):
    """The first relation of TEMPORAL under which other is related, or None"""
    relations = position.get_temporal_relations()
    for name in TEMPORAL:
        if other in relations.get(name, []):
            return name
    return None


tgis.init()
crew_a = read_track("crew_a.csv")
crew_b = read_track("crew_b.csv")
for positions in (crew_a, crew_b):
    tgis.AbstractSpaceTimeDataset.snap_map_list(positions)
    buffer_positions(positions)

builder = tgis.SpatioTemporalTopologyBuilder()
builder.build(mapsA=crew_a, mapsB=crew_b, spatial="2D")

for position in crew_a:
    for spatial, others in position.get_spatial_relations().items():
        if spatial not in SPATIAL:
            continue
        for other in others:
            temporal = temporal_relation(position, other)
            if temporal is None:
                continue
            space = position.spatial_intersection(other)
            time = position.temporal_intersection(other)
            print(
                "{:%H:%M}-{:%H:%M} {} m2 {} {}".format(
                    time.get_start_time(),
                    time.get_end_time(),
                    round(space.get_area()),
                    spatial.lower(),
                    temporal.lower(),
                )
            )
