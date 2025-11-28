"""
API views for reservation table operations.
"""

from datetime import timedelta
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from agv_data.models import ResourceAgent
from agv_data.serializers import BookingSerializer, ResourceAgentSerializer

from ..domain.value_objects import BookingRequest, SlotQuery, TimeSlot
from ..domain.exceptions import (
    BookingConflictError,
    ResourceNotFoundError,
    InvalidBookingError
)
from ..services import SlotFinderService, BookingService


class QuerySlotView(APIView):
    """
    Query the earliest available time slot for a resource (Exploring Ant).
    
    This endpoint is used by Exploring Ants to find when they can
    reserve a resource (Crossroad Agent or Logical Segment Agent).
    
    POST /api/agvs/reservation/resource/<int:resource_id>/query_slot/
    Body:
    {
        "request_start_time": "2025-11-07T15:30:00Z",
        "duration_seconds": 15
    }
    
    Response 200:
    {
        "resource_id": 1,
        "earliest_available_start": "2025-11-07T15:30:00Z",
        "requested_duration_seconds": 15,
        "calculated_delay_seconds": 0
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slot_finder = SlotFinderService()
    
    def post(self, request, resource_id, format=None):
        try:
            # Parse input
            start_time_str = request.data.get('request_start_time')
            duration_sec = request.data.get('duration_seconds')
            
            if not start_time_str or not duration_sec:
                return Response(
                    {"error": "Missing required fields: 'request_start_time' or 'duration_seconds'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            duration_sec = int(duration_sec)
            if duration_sec <= 0:
                return Response(
                    {"error": "duration_seconds must be positive"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            start_time = parse_datetime(start_time_str)
            if not start_time:
                return Response(
                    {"error": "Invalid 'request_start_time' format. Use ISO 8601 format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create query object
            query = SlotQuery(
                resource_id=resource_id,
                desired_start=start_time,
                duration=timedelta(seconds=duration_sec)
            )
            
            # Find earliest available slot
            earliest_slot_start = self.slot_finder.find_earliest_available_slot(query)
            
            # Calculate delay
            delay_seconds = (earliest_slot_start - start_time).total_seconds()
            
            return Response({
                "resource_id": resource_id,
                "earliest_available_start": earliest_slot_start.isoformat(),
                "requested_duration_seconds": duration_sec,
                "calculated_delay_seconds": delay_seconds
            }, status=status.HTTP_200_OK)
        
        except ResourceNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except (ValueError, InvalidBookingError) as e:
            return Response(
                {"error": f"Invalid input: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BookSlotView(APIView):
    """
    Create a booking for EXACT time slot (Intention Ant - STRICT MODE).
    
    This endpoint implements the critical strict/fail-fast approach:
    - ONLY books the EXACT slot requested (from Exploring Ant)
    - Returns 409 if ANY conflict exists
    - Does NOT auto-serialize or find alternatives
    
    Why this is critical for SSI-DMAS:
    - AGV bids based on specific slot from Exploring Ant
    - Intention Ant MUST get that exact slot or fail
    - Auto-serialization would break auction integrity
      (AGV wins for slot A but gets slot B with different cost)
    
    POST /api/agvs/reservation/resource/<int:resource_id>/book_slot/
    Body:
    {
        "agv_id": 2,
        "request_start_time": "2025-11-07T15:30:00Z",
        "duration_seconds": 15
    }
    
    Response 201:
    {
        "id": 123,
        "resource_id": 1,
        "agv_id": 2,
        "start_time": "2025-11-07T15:30:00Z",
        "end_time": "2025-11-07T15:30:15Z",
        "created_at": "2025-11-07T15:00:00Z"
    }
    
    Response 409 (Conflict - AGV must abort mission):
    {
        "error": "Exact time slot ... is already occupied. Auction result is invalid. AGV must re-bid."
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booking_service = BookingService()
    
    def post(self, request, resource_id, format=None):
        try:
            # Parse input
            agv_id = request.data.get('agv_id')
            start_time_str = request.data.get('request_start_time')
            duration_sec = request.data.get('duration_seconds')
            
            if not agv_id or not start_time_str or not duration_sec:
                return Response(
                    {"error": "Missing required fields: 'agv_id', 'request_start_time', or 'duration_seconds'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            agv_id = int(agv_id)
            duration_sec = int(duration_sec)
            
            if duration_sec <= 0:
                return Response(
                    {"error": "duration_seconds must be positive"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            start_time = parse_datetime(start_time_str)
            if not start_time:
                return Response(
                    {"error": "Invalid 'request_start_time' format. Use ISO 8601 format."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create booking request
            duration = timedelta(seconds=duration_sec)
            end_time = start_time + duration
            
            booking_request = BookingRequest(
                resource_id=resource_id,
                agv_id=agv_id,
                time_slot=TimeSlot(start_time=start_time, end_time=end_time)
            )
            
            # STRICT MODE: Book EXACT slot or fail with 409
            new_booking = self.booking_service.create_booking(booking_request)
            
            serializer = BookingSerializer(new_booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ResourceNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except BookingConflictError as e:
            # 409 Conflict: AGV must abort mission and return to idle
            return Response(
                {"error": str(e)},
                status=status.HTTP_409_CONFLICT
            )
        except (ValueError, InvalidBookingError) as e:
            return Response(
                {"error": f"Invalid input: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListBookingsView(APIView):
    """
    List bookings for an AGV or a resource.
    
    GET /api/agvs/reservation/bookings/?agv_id=<agv_id>&include_past=<true|false>
    GET /api/agvs/reservation/bookings/?resource_id=<resource_id>
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booking_service = BookingService()
    
    def get(self, request, format=None):
        agv_id = request.query_params.get('agv_id')
        resource_id = request.query_params.get('resource_id')
        
        try:
            if agv_id:
                agv_id = int(agv_id)
                include_past = request.query_params.get('include_past', 'false').lower() == 'true'
                bookings = self.booking_service.get_agv_bookings(agv_id, include_past)
            elif resource_id:
                resource_id = int(resource_id)
                bookings = self.booking_service.get_resource_bookings(resource_id)
            else:
                return Response(
                    {"error": "Must provide either 'agv_id' or 'resource_id' query parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = BookingSerializer(bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except ValueError:
            return Response(
                {"error": "Invalid agv_id or resource_id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CancelBookingView(APIView):
    """
    Cancel a specific booking.
    
    DELETE /api/agvs/reservation/bookings/<int:booking_id>/
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booking_service = BookingService()
    
    def delete(self, request, booking_id, format=None):
        try:
            success = self.booking_service.cancel_booking(booking_id)
            
            if success:
                return Response(
                    {"message": f"Booking {booking_id} cancelled successfully"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": f"Booking {booking_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListResourcesView(ListAPIView):
    """
    List all available resources (Crossroad Agents and Logical Segment Agents).
    
    GET /api/agvs/reservation/resources/
    """
    queryset = ResourceAgent.objects.all()
    serializer_class = ResourceAgentSerializer
