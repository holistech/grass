"""Former module of the topology builder, which now lives in topology.py

The old temporal algebra still imports the builder from here; the module
goes with it.
"""

from .topology import (
    SpatioTemporalTopologyBuilder,
    count_temporal_topology_relationships,
    create_temporal_relation_sql_where_statement,
    print_spatio_temporal_topology_relationships,
    set_spatial_relationship,
    set_temporal_relationship,
)

__all__ = [
    "SpatioTemporalTopologyBuilder",
    "count_temporal_topology_relationships",
    "create_temporal_relation_sql_where_statement",
    "print_spatio_temporal_topology_relationships",
    "set_spatial_relationship",
    "set_temporal_relationship",
]
