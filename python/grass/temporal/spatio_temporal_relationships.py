"""Former module of the topology builder, which now lives in topology.py

The old temporal algebra and the old aggregate_by_topology() still import
the builder from here; the module goes with them.
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
