"""
Service for creating bookings (Intention Ant operation).
"""

from django.db import transaction, DatabaseError
from agv_data.models import Booking
from ..domain.value_objects import BookingRequest, TimeSlot
from ..domain.exceptions import BookingConflictError
from ..repositories.resource_repository import ResourceRepository
from ..repositories.booking_repository import BookingRepository


class BookingService:
    """
    Service for creating and managing bookings.
    
    This implements the Intention Ant phase of D-MAS:
    - Books EXACT time slots (strict/fail-fast mode)
    - Returns 409 Conflict if slot is occupied
    - Ensures auction integrity (AGV gets exact slot or fails)
    """
    
    def __init__(self, 
                 resource_repo: ResourceRepository = None,
                 booking_repo: BookingRepository = None):
        self.resource_repo = resource_repo or ResourceRepository()
        self.booking_repo = booking_repo or BookingRepository()
    
    @transaction.atomic
    def create_booking(self, request: BookingRequest) -> Booking:
        """
        Create a booking for the EXACT time slot requested (STRICT MODE).
        
        This function implements the critical strict/fail-fast approach:
        - ONLY books the EXACT slot requested
        - Does NOT auto-serialize or find alternative slots
        - Returns 409 if ANY conflict exists
        
        Why this is critical for SSI-DMAS:
        - AGV bids based on specific slot from Exploring Ant
        - Intention Ant MUST get that exact slot or fail
        - Auto-serialization would break auction integrity
          (AGV wins for slot A but gets slot B with different cost)
        
        Args:
            request: BookingRequest containing resource_id, agv_id, and time_slot
            
        Returns:
            Created Booking instance
            
        Raises:
            ResourceNotFoundError: If resource does not exist
            BookingConflictError: If the EXACT slot is not available (409)
        """
        # Verify resource exists and LOCK it for this transaction
        # This prevents other transactions from checking this resource simultaneously
        self.resource_repo.find_by_id(request.resource_id, lock=True)
        
        # Check for conflicts with SELECT FOR UPDATE (locks conflicting rows)
        has_conflict = self.booking_repo.has_conflict(
            resource_id=request.resource_id,
            time_slot=request.time_slot,
            lock=True
        )
        
        if has_conflict:
            # FAIL-FAST: Exact slot is occupied, return 409
            # AGV must abort this mission and return to idle
            raise BookingConflictError(
                f"Exact time slot {request.time_slot.start_time} to "
                f"{request.time_slot.end_time} is already occupied. "
                f"Auction result is invalid. AGV must re-bid."
            )
        
        # No conflict! Create the booking for the EXACT slot
        try:
            return self.booking_repo.create(
                resource_id=request.resource_id,
                agv_id=request.agv_id,
                start_time=request.time_slot.start_time,
                end_time=request.time_slot.end_time
            )
        except DatabaseError as e:
            raise BookingConflictError(
                f"Failed to create booking due to database error: {str(e)}"
            )
    
    def cancel_booking(self, booking_id: int) -> bool:
        """
        Cancel a specific booking.
        
        Args:
            booking_id: ID of the booking to cancel
            
        Returns:
            True if booking was deleted, False if not found
        """
        return self.booking_repo.delete(booking_id)
    
    def cancel_agv_bookings(self, agv_id: int, future_only: bool = True) -> int:
        """
        Cancel all bookings for a specific AGV.
        
        Useful when:
        - AGV aborts a mission
        - AGV is reassigned to different task
        - System needs to free resources
        
        Args:
            agv_id: ID of the AGV
            future_only: If True, only cancel future bookings
            
        Returns:
            Number of bookings cancelled
        """
        return self.booking_repo.delete_by_agv(agv_id, future_only)
    
    def get_agv_bookings(self, agv_id: int, include_past: bool = False):
        """
        Get all bookings for a specific AGV.
        
        Args:
            agv_id: ID of the AGV
            include_past: If False, only return future bookings
            
        Returns:
            List of Booking objects
        """
        return self.booking_repo.find_by_agv(agv_id, include_past)
    
    def get_resource_bookings(self, resource_id: int, start_time=None, end_time=None):
        """
        Get all bookings for a specific resource.
        
        Args:
            resource_id: ID of the resource
            start_time: Optional start of time range
            end_time: Optional end of time range
            
        Returns:
            List of Booking objects
        """
        return self.booking_repo.find_by_resource(resource_id, start_time, end_time)
