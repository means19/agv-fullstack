"""Validation service for map data."""

import csv
import io
from typing import List
from ..constants import MapConstants
from ..exceptions import InvalidCSVFormatException, InvalidDirectionException


class MapValidationService:
    """Service for validating map data."""

    @staticmethod
    def validate_csv_data(data: str) -> List[List[str]]:
        """
        Validate and parse CSV data into a matrix.
        
        Args:
            data: Raw CSV string data
            
        Returns:
            List of lists representing the CSV matrix
            
        Raises:
            InvalidCSVFormatException: If CSV format is invalid
        """
        try:
            matrix = list(csv.reader(io.StringIO(data)))
            
            if not matrix:
                raise InvalidCSVFormatException("CSV data is empty")
            
            # Validate square matrix
            expected_columns = len(matrix)
            for row_idx, row in enumerate(matrix):
                if len(row) != expected_columns:
                    raise InvalidCSVFormatException(
                        f"Row {row_idx} has {len(row)} columns, expected {expected_columns}"
                    )
            
            return matrix
            
        except csv.Error as e:
            raise InvalidCSVFormatException(f"Invalid CSV format: {str(e)}")
        except Exception as e:
            raise InvalidCSVFormatException(f"Error parsing CSV: {str(e)}")

    @staticmethod
    def validate_direction_value(value: int) -> bool:
        """
        Validate that direction value is acceptable.
        
        Args:
            value: Direction value to validate
            
        Returns:
            True if valid
            
        Raises:
            InvalidDirectionException: If direction value is invalid
        """
        if value != MapConstants.NO_CONNECTION and not (1 <= value <= 4):
            raise InvalidDirectionException(
                f"Invalid direction value {value}. Must be 1-4 or {MapConstants.NO_CONNECTION}"
            )
        return True

    @staticmethod
    def validate_distance_value(value: float) -> bool:
        """
        Validate that distance value is acceptable.
        
        Args:
            value: Distance value to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If distance is negative
        """
        if value < 0 and value != MapConstants.NO_CONNECTION:
            raise ValueError(f"Distance cannot be negative: {value}")
        return True

    @staticmethod
    def is_valid_connection(node1: int, node2: int, value: float) -> bool:
        """
        Check if a connection is valid (not a self-loop and not NO_CONNECTION).
        
        Args:
            node1: First node ID
            node2: Second node ID
            value: Connection value
            
        Returns:
            True if valid connection, False otherwise
        """
        return node1 != node2 and value != MapConstants.NO_CONNECTION
