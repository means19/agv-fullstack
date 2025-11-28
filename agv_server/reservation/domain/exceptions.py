"""
Domain exceptions for Reservation Table.
"""


class ReservationError(Exception):
    """Base exception for reservation-related errors."""
    pass


class BookingConflictError(ReservationError):
    """
    Raised when attempting to book a time slot that is already reserved.
    
    This is a CRITICAL exception in SSI-DMAS algorithm:
    - Ensures auction integrity
    - AGV must get exact slot or fail
    - No auto-serialization to prevent cost mismatch
    """
    pass


class ResourceNotFoundError(ReservationError):
    """Raised when a ResourceAgent ID does not exist."""
    pass


class InvalidBookingError(ReservationError):
    """Raised when booking parameters are invalid."""
    pass
