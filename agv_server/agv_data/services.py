"""
Service layer for Reservation Table operations.
Implements the core logic for D-MAS (Delegate Multi-Agent System) resource booking.
"""

from django.db import transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone
from .models import ResourceAgent, Booking
from datetime import timedelta


class BookingConflictError(Exception):
    """Raised when a booking conflict cannot be resolved."""
    pass


class ResourceNotFoundError(Exception):
    """Raised when a ResourceAgent ID does not exist."""
    pass


@transaction.atomic
def find_earliest_available_slot(
    resource_id: int,
    request_start_time: timezone.datetime,
    duration: timedelta
):
    """
    Find the earliest available time slot for a resource (Exploring Ant operation).
    
    This function searches for the earliest time slot that can accommodate the requested
    duration, starting from request_start_time. It uses database-level locking to ensure
    consistency in concurrent environments.
    
    Args:
        resource_id: ID of the ResourceAgent (CA or LSA)
        request_start_time: Earliest acceptable start time for the booking
        duration: Required duration of the booking
        
    Returns:
        datetime: The earliest available start time for the booking
        
    Raises:
        ValueError: If duration is not positive
        ResourceNotFoundError: If resource_id does not exist
    """
    if duration <= timedelta(seconds=0):
        raise ValueError("Duration must be positive.")
    
    # Verify resource exists
    try:
        resource = ResourceAgent.objects.select_for_update().get(id=resource_id)
    except ResourceAgent.DoesNotExist:
        raise ResourceNotFoundError(f"Resource with ID={resource_id} does not exist.")
    
    current_check_time = request_start_time
    
    # Iteratively find the earliest available slot
    while True:
        request_end_time = current_check_time + duration
        
        # Find any conflicting booking
        conflicting_booking = Booking.objects.select_for_update().filter(
            resource_id=resource_id,
            start_time__lt=request_end_time,
            end_time__gt=current_check_time
        ).order_by('end_time').first()
        
        if conflicting_booking:
            # Move to the end of the conflicting booking and try again
            current_check_time = conflicting_booking.end_time
        else:
            # No conflict found, this slot is available
            return current_check_time


@transaction.atomic
def create_booking(
    resource_id: int,
    agv_id: int,
    exact_start_time: timezone.datetime,
    duration: timedelta
):
    """
    Create a booking for an AGV (Intention Ant operation) - STRICT MODE.
    
    This function ONLY books the EXACT time slot requested. It does NOT automatically
    find alternative slots. This ensures auction integrity in SSI-DMAS:
    - AGV bids based on a specific slot from Exploring Ant
    - Intention Ant must get that EXACT slot or fail with 409
    - If it fails, AGV returns to idle and can bid on a new auction
    
    This is CRITICAL: Auto-serialization would break auction integrity because
    AGV would win auction for slot A but receive slot B with different cost.
    
    Args:
        resource_id: ID of the ResourceAgent (CA or LSA)
        agv_id: ID of the AGV making the booking
        exact_start_time: The EXACT start time that must be available (from EA)
        duration: Required duration of the booking
        
    Returns:
        Booking: The created booking instance
        
    Raises:
        ResourceNotFoundError: If resource_id does not exist
        BookingConflictError: If the EXACT slot is not available (409)
        ValueError: If duration is not positive
    """
    # Verify resource exists and LOCK it for the duration of this transaction
    # This prevents other transactions from even checking this resource
    try:
        resource = ResourceAgent.objects.select_for_update().get(id=resource_id)
    except ResourceAgent.DoesNotExist:
        raise ResourceNotFoundError(f"Resource with ID={resource_id} does not exist.")
    
    if duration <= timedelta(seconds=0):
        raise ValueError("Duration must be positive.")
    
    exact_end_time = exact_start_time + duration
    
    # CHECK FOR CONFLICTS with SELECT FOR UPDATE (locks the conflicting rows)
    # This ensures no other transaction can create conflicting bookings
    conflicts = Booking.objects.select_for_update().filter(
        resource_id=resource_id,
        start_time__lt=exact_end_time,    # Conflict if it starts before we end
        end_time__gt=exact_start_time      # AND it ends after we start
    ).exists()
    
    if conflicts:
        # FAIL-FAST: Exact slot is occupied, return 409
        # AGV must abort this mission and return to idle state
        raise BookingConflictError(
            f"Exact time slot {exact_start_time} to {exact_end_time} is already occupied. "
            f"Auction result is invalid. AGV must re-bid."
        )
    
    # No conflict! Create the booking for the EXACT slot
    try:
        new_booking = Booking.objects.create(
            resource_id=resource_id,
            agv_id=agv_id,
            start_time=exact_start_time,
            end_time=exact_end_time
        )
        return new_booking
    except DatabaseError as e:
        raise BookingConflictError(f"Failed to create booking due to database error: {str(e)}")


def get_bookings_for_agv(agv_id: int, include_past: bool = False):
    """
    Get all bookings for a specific AGV.
    
    Args:
        agv_id: ID of the AGV
        include_past: If False, only return future/current bookings
        
    Returns:
        QuerySet of Booking objects
    """
    bookings = Booking.objects.filter(agv_id=agv_id).select_related('resource')
    
    if not include_past:
        bookings = bookings.filter(end_time__gte=timezone.now())
    
    return bookings.order_by('start_time')


def get_bookings_for_resource(resource_id: int, start_time=None, end_time=None):
    """
    Get all bookings for a specific resource within a time range.
    
    Args:
        resource_id: ID of the ResourceAgent
        start_time: Optional start of time range
        end_time: Optional end of time range
        
    Returns:
        QuerySet of Booking objects
    """
    bookings = Booking.objects.filter(resource_id=resource_id)
    
    if start_time:
        bookings = bookings.filter(end_time__gte=start_time)
    if end_time:
        bookings = bookings.filter(start_time__lte=end_time)
    
    return bookings.order_by('start_time')


def cancel_booking(booking_id: int):
    """
    Cancel a booking by deleting it.
    
    Args:
        booking_id: ID of the booking to cancel
        
    Returns:
        bool: True if booking was deleted, False if not found
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        booking.delete()
        return True
    except Booking.DoesNotExist:
        return False


def cancel_agv_bookings(agv_id: int, future_only: bool = True):
    """
    Cancel all bookings for a specific AGV.
    
    Args:
        agv_id: ID of the AGV
        future_only: If True, only cancel future bookings
        
    Returns:
        int: Number of bookings cancelled
    """
    bookings = Booking.objects.filter(agv_id=agv_id)
    
    if future_only:
        bookings = bookings.filter(start_time__gt=timezone.now())
    
    count, _ = bookings.delete()
    return count
