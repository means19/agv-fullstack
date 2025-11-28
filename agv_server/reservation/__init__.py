"""
Reservation Table Module

Clean architecture implementation for D-MAS resource reservation system.
Provides time-based booking for Crossroad Agents (CA) and Logical Segment Agents (LSA).
"""

from .domain.exceptions import (
    BookingConflictError, 
    ResourceNotFoundError, 
    InvalidBookingError
)
from .domain.value_objects import TimeSlot, BookingRequest, SlotQuery
from .services.slot_finder_service import SlotFinderService
from .services.booking_service import BookingService
from .repositories.booking_repository import BookingRepository
from .repositories.resource_repository import ResourceRepository

__all__ = [
    # Exceptions
    'BookingConflictError',
    'ResourceNotFoundError',
    'InvalidBookingError',
    
    # Value Objects
    'TimeSlot',
    'BookingRequest',
    'SlotQuery',
    
    # Services
    'SlotFinderService',
    'BookingService',
    
    # Repositories
    'BookingRepository',
    'ResourceRepository',
]
