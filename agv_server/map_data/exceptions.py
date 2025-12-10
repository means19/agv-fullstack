"""Custom exceptions for map data operations."""


class MapDataException(Exception):
    """Base exception for map data operations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.message = message
        self.extra_data = kwargs


class InvalidMapDataException(MapDataException):
    """Raised when map data format is invalid."""
    pass


class MapDataNotFoundException(MapDataException):
    """Raised when requested map data is not found."""
    pass


class MapDataImportException(MapDataException):
    """Raised when map data import fails."""
    pass


class InvalidCSVFormatException(MapDataException):
    """Raised when CSV format is invalid."""
    pass


class InvalidDirectionException(MapDataException):
    """Raised when direction value is invalid."""
    pass
