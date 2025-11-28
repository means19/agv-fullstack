"""
Value objects for Reservation domain.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class TimeSlot:
    """
    Immutable value object representing a time interval.
    
    Attributes:
        start_time: When the slot begins
        end_time: When the slot ends
    """
    start_time: datetime
    end_time: datetime
    
    def __post_init__(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
    
    @property
    def duration(self) -> timedelta:
        """Get the duration of this time slot."""
        return self.end_time - self.start_time
    
    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """
        Check if this time slot overlaps with another.
        
        Returns True if there is any time overlap between the two slots.
        """
        return (self.start_time < other.end_time and 
                self.end_time > other.start_time)
    
    def __repr__(self) -> str:
        return f"TimeSlot({self.start_time} → {self.end_time})"


@dataclass(frozen=True)
class BookingRequest:
    """
    Immutable value object for booking request parameters.
    
    Attributes:
        resource_id: ID of the resource to book
        agv_id: ID of the AGV making the booking
        time_slot: The requested time slot
    """
    resource_id: int
    agv_id: int
    time_slot: TimeSlot
    
    @classmethod
    def create(cls, resource_id: int, agv_id: int, 
               start_time: datetime, duration: timedelta) -> 'BookingRequest':
        """
        Factory method to create a BookingRequest.
        
        Args:
            resource_id: ID of the resource to book
            agv_id: ID of the AGV making the booking
            start_time: When the booking should start
            duration: How long the booking should last
            
        Returns:
            BookingRequest instance
        """
        if duration <= timedelta(0):
            raise ValueError("Duration must be positive")
        
        time_slot = TimeSlot(
            start_time=start_time,
            end_time=start_time + duration
        )
        return cls(resource_id=resource_id, agv_id=agv_id, time_slot=time_slot)


@dataclass(frozen=True)
class SlotQuery:
    """
    Immutable value object for slot availability query.
    
    Attributes:
        resource_id: ID of the resource to query
        desired_start: Earliest acceptable start time
        duration: Required duration
    """
    resource_id: int
    desired_start: datetime
    duration: timedelta
    
    def __post_init__(self):
        if self.duration <= timedelta(0):
            raise ValueError("Duration must be positive")
