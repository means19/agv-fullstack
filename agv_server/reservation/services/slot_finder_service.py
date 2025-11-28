"""
Service for finding available time slots (Exploring Ant operation).
"""

from datetime import datetime
from django.db import transaction
from ..domain.value_objects import SlotQuery, TimeSlot
from ..repositories.resource_repository import ResourceRepository
from ..repositories.booking_repository import BookingRepository


class SlotFinderService:
    """
    Service for finding earliest available time slots.
    
    This implements the Exploring Ant phase of D-MAS:
    - Queries for available slots WITHOUT making reservations
    - Used for cost calculation in auction bidding
    - Multiple AGVs can query simultaneously
    """
    
    def __init__(self, 
                 resource_repo: ResourceRepository = None,
                 booking_repo: BookingRepository = None):
        self.resource_repo = resource_repo or ResourceRepository()
        self.booking_repo = booking_repo or BookingRepository()
    
    @transaction.atomic
    def find_earliest_available_slot(self, query: SlotQuery) -> datetime:
        """
        Find the earliest time slot that can accommodate the requested duration.
        
        Algorithm:
        1. Verify resource exists
        2. Get all conflicting bookings sorted by start time
        3. Iteratively check each potential slot
        4. Return first slot with no conflicts
        
        Args:
            query: SlotQuery containing resource_id, desired_start, and duration
            
        Returns:
            datetime: The earliest available start time (may be later than desired)
            
        Raises:
            ResourceNotFoundError: If resource does not exist
        """
        # Verify resource exists and lock it
        self.resource_repo.find_by_id(query.resource_id, lock=True)
        
        candidate_start = query.desired_start
        
        # Iteratively find the first available slot
        while True:
            candidate_slot = TimeSlot(
                start_time=candidate_start,
                end_time=candidate_start + query.duration
            )
            
            # Find conflicts (with lock to prevent race conditions)
            conflicts = self.booking_repo.find_conflicting_bookings(
                resource_id=query.resource_id,
                time_slot=candidate_slot,
                lock=True
            )
            
            if not conflicts:
                # No conflicts found - this slot is available
                return candidate_start
            
            # Move to the end of the first conflicting booking
            # Since bookings are sorted by start_time, we can optimize
            first_conflict = conflicts[0]
            candidate_start = first_conflict.end_time
