"""
Repository for Booking operations.
"""

from typing import List, Optional
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from agv_data.models import Booking
from ..domain.value_objects import TimeSlot


class BookingRepository:
    """
    Repository for Booking persistence operations.
    Handles database access for booking entities.
    """
    
    @transaction.atomic
    def create(self, resource_id: int, agv_id: int, 
               start_time: datetime, end_time: datetime) -> Booking:
        """
        Create a new booking.
        
        Args:
            resource_id: ID of the resource being booked
            agv_id: ID of the AGV making the booking
            start_time: When the booking starts
            end_time: When the booking ends
            
        Returns:
            Created Booking instance
        """
        return Booking.objects.create(
            resource_id=resource_id,
            agv_id=agv_id,
            start_time=start_time,
            end_time=end_time
        )
    
    @transaction.atomic
    def find_conflicting_bookings(
        self, 
        resource_id: int, 
        time_slot: TimeSlot,
        lock: bool = False
    ) -> List[Booking]:
        """
        Find all bookings that conflict with the given time slot.
        
        A conflict exists if:
        - booking.start_time < time_slot.end_time AND
        - booking.end_time > time_slot.start_time
        
        Args:
            resource_id: ID of the resource
            time_slot: The time slot to check for conflicts
            lock: If True, acquire database locks on found bookings
            
        Returns:
            List of conflicting Booking objects
        """
        queryset = Booking.objects.filter(
            resource_id=resource_id,
            start_time__lt=time_slot.end_time,
            end_time__gt=time_slot.start_time
        )
        
        if lock:
            queryset = queryset.select_for_update()
        
        return list(queryset.order_by('start_time'))
    
    def has_conflict(self, resource_id: int, time_slot: TimeSlot, 
                     lock: bool = False) -> bool:
        """
        Check if any booking conflicts with the given time slot.
        
        Args:
            resource_id: ID of the resource
            time_slot: The time slot to check
            lock: If True, acquire database locks
            
        Returns:
            True if at least one conflict exists
        """
        queryset = Booking.objects.filter(
            resource_id=resource_id,
            start_time__lt=time_slot.end_time,
            end_time__gt=time_slot.start_time
        )
        
        if lock:
            queryset = queryset.select_for_update()
        
        return queryset.exists()
    
    def find_by_agv(self, agv_id: int, include_past: bool = False) -> List[Booking]:
        """
        Get all bookings for a specific AGV.
        
        Args:
            agv_id: ID of the AGV
            include_past: If False, only return future bookings
            
        Returns:
            List of Booking objects
        """
        queryset = Booking.objects.filter(agv_id=agv_id).select_related('resource')
        
        if not include_past:
            queryset = queryset.filter(end_time__gte=timezone.now())
        
        return list(queryset.order_by('start_time'))
    
    def find_by_resource(
        self, 
        resource_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Booking]:
        """
        Get all bookings for a specific resource within a time range.
        
        Args:
            resource_id: ID of the resource
            start_time: Optional start of time range
            end_time: Optional end of time range
            
        Returns:
            List of Booking objects
        """
        queryset = Booking.objects.filter(resource_id=resource_id)
        
        if start_time:
            queryset = queryset.filter(end_time__gte=start_time)
        if end_time:
            queryset = queryset.filter(start_time__lte=end_time)
        
        return list(queryset.order_by('start_time'))
    
    def find_by_id(self, booking_id: int) -> Optional[Booking]:
        """Find a booking by its ID."""
        try:
            return Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return None
    
    @transaction.atomic
    def delete(self, booking_id: int) -> bool:
        """
        Delete a booking by its ID.
        
        Returns:
            True if booking was deleted, False if not found
        """
        booking = self.find_by_id(booking_id)
        if booking:
            booking.delete()
            return True
        return False
    
    @transaction.atomic
    def delete_by_agv(self, agv_id: int, future_only: bool = True) -> int:
        """
        Delete all bookings for a specific AGV.
        
        Args:
            agv_id: ID of the AGV
            future_only: If True, only delete future bookings
            
        Returns:
            Number of bookings deleted
        """
        queryset = Booking.objects.filter(agv_id=agv_id)
        
        if future_only:
            queryset = queryset.filter(start_time__gt=timezone.now())
        
        count, _ = queryset.delete()
        return count
