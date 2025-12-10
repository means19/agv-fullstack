"""Views for handling map data operations."""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import MapImportService, MapQueryService
from .exceptions import (
    MapDataException,
    MapDataNotFoundException,
    MapDataImportException,
)
from .constants import ErrorMessages, LogMessages

logger = logging.getLogger(__name__)


class ImportConnectionsAPIView(APIView):
    """API endpoint for importing connection data from CSV."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.import_service = MapImportService()

    def post(self, request):
        """
        Import connection data from CSV file.
        
        Request body should contain raw CSV data as string.
        """
        try:
            data = request.body.decode("utf-8")
            result = self.import_service.import_connections(data)

            logger.info(
                LogMessages.IMPORT_CONNECTIONS.format(result["connection_count"])
            )
            return Response(result, status=status.HTTP_200_OK)

        except MapDataImportException as e:
            logger.error(str(e))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(ErrorMessages.IMPORT_ERROR.format(str(e)))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ImportDirectionsAPIView(APIView):
    """API endpoint for importing direction data from CSV."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.import_service = MapImportService()

    def post(self, request):
        """
        Import direction data from CSV file.
        
        Request body should contain raw CSV data as string.
        """
        try:
            data = request.body.decode("utf-8")
            result = self.import_service.import_directions(data)

            logger.info(LogMessages.IMPORT_DIRECTIONS.format(result["direction_count"]))
            return Response(result, status=status.HTTP_200_OK)

        except MapDataImportException as e:
            logger.error(str(e))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(ErrorMessages.IMPORT_ERROR.format(str(e)))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MapDataAPIView(APIView):
    """API endpoint for retrieving complete map data."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_service = MapQueryService()

    def get(self, request):
        """
        Get all map data including nodes, connections, and directions.
        
        Returns 200 with complete data or 206/404 for partial/missing data.
        """
        try:
            data = self.query_service.get_complete_map_data()
            return Response(
                {"success": True, "data": data}, status=status.HTTP_200_OK
            )

        except MapDataNotFoundException as e:
            logger.warning(str(e))
            # Return 206 Partial Content if some data exists
            status_code = (
                status.HTTP_206_PARTIAL_CONTENT
                if e.extra_data.get("available")
                else status.HTTP_404_NOT_FOUND
            )
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "missing": e.extra_data.get("missing", []),
                    "available": e.extra_data.get("available"),
                },
                status=status_code,
            )
        except Exception as e:
            logger.error(str(e))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteMapDataAPIView(APIView):
    """API endpoint for deleting all map data."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_service = MapQueryService()

    def post(self, request):
        """
        Delete all map data from database.
        
        Returns deletion statistics.
        """
        try:
            result = self.query_service.delete_all_map_data()

            logger.info(LogMessages.DELETE_SUCCESS)
            return Response(
                {"success": True, "deleted": result}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(LogMessages.DELETE_ERROR.format(str(e)))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MapStatisticsAPIView(APIView):
    """API endpoint for retrieving map statistics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_service = MapQueryService()

    def get(self, request):
        """Get statistical information about the map."""
        try:
            stats = self.query_service.get_map_statistics()
            return Response({"success": True, "statistics": stats}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(str(e))
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
