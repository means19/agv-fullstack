"""Query service for map data."""

from typing import Dict, List, Any, Optional
from django.db.models import Q
from ..models import MapData, Connection, Direction
from ..exceptions import MapDataNotFoundException


class MapQueryService:
    """Service for querying map data."""

    @staticmethod
    def get_all_nodes() -> List[int]:
        """
        Get list of all unique nodes from directions.
        
        Returns:
            List of node IDs
        """
        return list(Direction.objects.values_list("node1", flat=True).distinct())

    @staticmethod
    def get_all_connections() -> List[Dict[str, Any]]:
        """
        Get all connections as dictionaries.
        
        Returns:
            List of connection data
        """
        return list(Connection.objects.values())

    @staticmethod
    def get_all_directions() -> List[Dict[str, Any]]:
        """
        Get all directions as dictionaries.
        
        Returns:
            List of direction data
        """
        return list(Direction.objects.values())

    @staticmethod
    def get_connections_for_node(node_id: int) -> List[Connection]:
        """
        Get all connections involving a specific node.
        
        Args:
            node_id: Node ID to query
            
        Returns:
            List of Connection objects
        """
        return list(Connection.objects.get_connections_for_node(node_id))

    @staticmethod
    def get_directions_for_node(node_id: int) -> List[Direction]:
        """
        Get all directions from a specific node.
        
        Args:
            node_id: Node ID to query
            
        Returns:
            List of Direction objects
        """
        return list(Direction.objects.get_directions_for_node(node_id))

    @staticmethod
    def get_distance_between_nodes(node1: int, node2: int) -> Optional[float]:
        """
        Get distance between two nodes.
        
        Args:
            node1: First node ID
            node2: Second node ID
            
        Returns:
            Distance value or None if no connection exists
        """
        return Connection.objects.get_distance(node1, node2)

    @staticmethod
    def get_direction_between_nodes(node1: int, node2: int) -> Optional[int]:
        """
        Get direction from node1 to node2.
        
        Args:
            node1: Starting node ID
            node2: Ending node ID
            
        Returns:
            Direction value or None if no direction exists
        """
        return Direction.objects.get_direction(node1, node2)

    @staticmethod
    def get_complete_map_data() -> Dict[str, Any]:
        """
        Get all map data including nodes, connections, and directions.
        
        Returns:
            Dictionary with complete map data
            
        Raises:
            MapDataNotFoundException: If map data is missing or incomplete
        """
        nodes = MapQueryService.get_all_nodes()
        connections = MapQueryService.get_all_connections()
        directions = MapQueryService.get_all_directions()

        has_connections = bool(connections)
        has_directions = bool(directions)

        # Check for missing data
        if not has_connections and not has_directions:
            raise MapDataNotFoundException(
                "No map data available. Please import both connection and direction data.",
                missing=["connections", "directions"],
            )

        if not has_connections:
            raise MapDataNotFoundException(
                "Connection data is missing. Please import the connections CSV file.",
                missing=["connections"],
                available={"nodes": nodes, "directions": directions},
            )

        if not has_directions:
            raise MapDataNotFoundException(
                "Direction data is missing. Please import the directions CSV file.",
                missing=["directions"],
                available={
                    "nodes": list(
                        Connection.objects.values_list("node1", flat=True).distinct()
                    ),
                    "connections": connections,
                },
            )

        return {
            "nodes": nodes,
            "connections": connections,
            "directions": directions,
            "node_count": len(nodes),
            "connection_count": len(connections),
            "direction_count": len(directions),
        }

    @staticmethod
    def get_map_statistics() -> Dict[str, int]:
        """
        Get statistical information about the map.
        
        Returns:
            Dictionary with map statistics
        """
        return {
            "total_nodes": Direction.objects.values_list(
                "node1", flat=True
            ).distinct().count(),
            "total_connections": Connection.objects.count(),
            "total_directions": Direction.objects.count(),
            "map_data_entries": MapData.objects.count(),
        }

    @staticmethod
    def delete_all_map_data() -> Dict[str, Any]:
        """
        Delete all map data from database.
        
        Returns:
            Dictionary with deletion details
        """
        connections_count = Connection.objects.count()
        directions_count = Direction.objects.count()
        map_data_count = MapData.objects.count()

        Connection.objects.all().delete()
        Direction.objects.all().delete()
        MapData.objects.all().delete()

        return {
            "deleted_connections": connections_count,
            "deleted_directions": directions_count,
            "deleted_map_data": map_data_count,
        }
