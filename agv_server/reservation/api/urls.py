"""
URL configuration for reservation table API.
"""

from django.urls import path
from .views import (
    QuerySlotView,
    BookSlotView,
    ListBookingsView,
    CancelBookingView,
    ListResourcesView,
)

app_name = 'reservation'

urlpatterns = [
    # Resource management
    path('resources/', ListResourcesView.as_view(), name='list-resources'),
    
    # Slot operations (D-MAS)
    path('resource/<int:resource_id>/query_slot/', QuerySlotView.as_view(), name='query-slot'),
    path('resource/<int:resource_id>/book_slot/', BookSlotView.as_view(), name='book-slot'),
    
    # Booking management
    path('bookings/', ListBookingsView.as_view(), name='list-bookings'),
    path('bookings/<int:booking_id>/', CancelBookingView.as_view(), name='cancel-booking'),
]
