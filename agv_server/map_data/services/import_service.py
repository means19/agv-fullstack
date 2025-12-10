"""Import service for map data."""

from typing import List, Dict, Any
from django.db import transaction
from ..models import MapData, Connection, Direction
from ..constants import MapConstants
from ..exceptions import MapDataImportException
from .validation_service import MapValidationService


class MapImportService:
    """Service for importing map data from CSV files."""

    def __init__(self):
        self.validation_service = MapValidationService()

    @transaction.atomic
    def import_connections(self, data: str) -> Dict[str, Any]:
        """
        Import connection data from CSV.
        
        Args:
            data: Raw CSV string data
            
        Returns:
            Dictionary with success status and import details
            
        Raises:
            MapDataImportException: If import fails
        """
        try:
            # Validate and parse CSV
            matrix = self.validation_service.validate_csv_data(data)
            node_count = len(matrix)

            # Update map data
            MapData.objects.update_node_count(node_count)

            # Process connections
            connections = self._extract_connections_from_matrix(matrix)

            # Bulk create
            Connection.objects.bulk_create_connections(connections)

            return {
                "success": True,
                "message": "Connection data imported successfully",
                "connection_count": len(connections),
                "node_count": node_count,
            }

        except Exception as e:
            raise MapDataImportException(f"Error importing connections: {str(e)}")

    @transaction.atomic
    def import_directions(self, data: str) -> Dict[str, Any]:
        """
        Import direction data from CSV.
        
        Args:
            data: Raw CSV string data
            
        Returns:
            Dictionary with success status and import details
            
        Raises:
            MapDataImportException: If import fails
        """
        try:
            # Validate and parse CSV
            matrix = self.validation_service.validate_csv_data(data)

            # Process directions
            directions = self._extract_directions_from_matrix(matrix)

            # Bulk create
            Direction.objects.bulk_create_directions(directions)

            return {
                "success": True,
                "message": "Direction data imported successfully",
                "direction_count": len(directions),
            }

        except Exception as e:
            raise MapDataImportException(f"Error importing directions: {str(e)}")

    def _extract_connections_from_matrix(
        self, matrix: List[List[str]]
    ) -> List[Connection]:
        """
        Extract connection objects from CSV matrix.
        
        Args:
            matrix: CSV data as list of lists
            
        Returns:
            List of Connection objects ready for bulk creation
        """
        connections = []
        
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                node1 = i + MapConstants.NODE_INDEX_OFFSET
                node2 = j + MapConstants.NODE_INDEX_OFFSET
                
                try:
                    distance = float(matrix[i][j])
                except ValueError:
                    continue  # Skip invalid values
                
                # Validate and add connection
                if self.validation_service.is_valid_connection(node1, node2, distance):
                    self.validation_service.validate_distance_value(distance)
                    connections.append(
                        Connection(node1=node1, node2=node2, distance=distance)
                    )
        
        return connections

    def _extract_directions_from_matrix(
        self, matrix: List[List[str]]
    ) -> List[Direction]:
        """
        Extract direction objects from CSV matrix.
        
        Args:
            matrix: CSV data as list of lists
            
        Returns:
            List of Direction objects ready for bulk creation
        """
        directions = []
        
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                node1 = i + MapConstants.NODE_INDEX_OFFSET
                node2 = j + MapConstants.NODE_INDEX_OFFSET
                
                try:
                    direction_value = int(matrix[i][j])
                except ValueError:
                    continue  # Skip invalid values
                
                # Validate and add direction
                if self.validation_service.is_valid_connection(
                    node1, node2, direction_value
                ):
                    self.validation_service.validate_direction_value(direction_value)
                    directions.append(
                        Direction(node1=node1, node2=node2, direction=direction_value)
                    )
        
        return directions
