# Reservation Module Quick Reference

## Import Cheat Sheet

```python
# Exceptions
from reservation import (
    BookingConflictError,      # 409 - Slot occupied
    ResourceNotFoundError,      # 404 - Resource not found
    InvalidBookingError,        # 400 - Invalid input
)

# Value Objects (immutable, self-validating)
from reservation import (
    TimeSlot,                   # Time interval with overlap detection
    BookingRequest,             # Factory for booking creation
    SlotQuery,                  # Query parameters for slot search
)

# Services
from reservation import (
    SlotFinderService,          # Exploring Ant operations
    BookingService,             # Intention Ant operations
)

# Repositories (for advanced use or testing)
from reservation import (
    ResourceRepository,         # Resource data access
    BookingRepository,          # Booking data access
)

# API Views (for URL routing)
from reservation.api import (
    QuerySlotView,              # POST /query_slot/
    BookSlotView,               # POST /book_slot/
    ListBookingsView,           # GET /bookings/
    CancelBookingView,          # DELETE /bookings/<id>/
    ListResourcesView,          # GET /resources/
)
```

## Common Use Cases

### 1. Find Earliest Available Slot (Exploring Ant)

```python
from datetime import datetime, timedelta
from reservation import SlotFinderService, SlotQuery

slot_finder = SlotFinderService()
query = SlotQuery(
    resource_id=1,
    requested_start_time=datetime.now(),
    duration=timedelta(seconds=15)
)

earliest_start = slot_finder.find_earliest_available_slot(query)
print(f"Resource available at: {earliest_start}")
```

### 2. Book Exact Slot (Intention Ant - STRICT)

```python
from reservation import BookingService, BookingRequest, TimeSlot, BookingConflictError

booking_service = BookingService()
try:
    booking = booking_service.create_booking(
        BookingRequest(
            resource_id=1,
            agv_id=2,
            time_slot=TimeSlot(
                start_time=earliest_start,
                end_time=earliest_start + timedelta(seconds=15)
            )
        )
    )
    print(f"Booking ID: {booking.id}")
except BookingConflictError as e:
    print(f"CONFLICT! AGV must abort mission: {e}")
```

### 3. List AGV's Bookings

```python
booking_service = BookingService()

# Only future bookings
future_bookings = booking_service.get_agv_bookings(agv_id=2, include_past=False)

# All bookings (including past)
all_bookings = booking_service.get_agv_bookings(agv_id=2, include_past=True)
```

### 4. Cancel Booking

```python
booking_service = BookingService()

# Cancel specific booking
success = booking_service.cancel_booking(booking_id=123)

# Bulk cancel AGV's future bookings (e.g., when aborting mission)
num_cancelled = booking_service.cancel_agv_bookings(agv_id=2, future_only=True)
```

### 5. Check Resource Availability (Low-level)

```python
from reservation import BookingRepository, TimeSlot

booking_repo = BookingRepository()

# Check if time slot is available
is_free = not booking_repo.has_conflict(
    resource_id=1,
    time_slot=TimeSlot(
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=15)
    )
)
```

## API Endpoint Reference

### POST /api/agvs/reservation/resource/{resource_id}/query_slot/

**Request:**
```json
{
  "request_start_time": "2025-11-27T15:30:00Z",
  "duration_seconds": 15
}
```

**Response 200:**
```json
{
  "resource_id": 1,
  "earliest_available_start": "2025-11-27T15:30:00Z",
  "requested_duration_seconds": 15,
  "calculated_delay_seconds": 0
}
```

---

### POST /api/agvs/reservation/resource/{resource_id}/book_slot/

**Request:**
```json
{
  "agv_id": 2,
  "request_start_time": "2025-11-27T15:30:00Z",
  "duration_seconds": 15
}
```

**Response 201 (Success):**
```json
{
  "id": 123,
  "resource_id": 1,
  "agv_id": 2,
  "start_time": "2025-11-27T15:30:00Z",
  "end_time": "2025-11-27T15:30:15Z",
  "created_at": "2025-11-27T15:00:00Z"
}
```

**Response 409 (Conflict - AGV must abort):**
```json
{
  "error": "Exact time slot 2025-11-27T15:30:00Z to 2025-11-27T15:30:15Z is already occupied. Auction result is invalid. AGV must re-bid."
}
```

---

### GET /api/agvs/reservation/bookings/?agv_id={agv_id}&include_past={true|false}

**Response 200:**
```json
[
  {
    "id": 123,
    "resource_id": 1,
    "agv_id": 2,
    "start_time": "2025-11-27T15:30:00Z",
    "end_time": "2025-11-27T15:30:15Z",
    "created_at": "2025-11-27T15:00:00Z"
  }
]
```

---

### GET /api/agvs/reservation/bookings/?resource_id={resource_id}

**Response 200:**
```json
[
  {
    "id": 123,
    "resource_id": 1,
    "agv_id": 2,
    "start_time": "2025-11-27T15:30:00Z",
    "end_time": "2025-11-27T15:30:15Z",
    "created_at": "2025-11-27T15:00:00Z"
  }
]
```

---

### DELETE /api/agvs/reservation/bookings/{booking_id}/

**Response 200:**
```json
{
  "message": "Booking 123 cancelled successfully"
}
```

**Response 404:**
```json
{
  "error": "Booking 123 not found"
}
```

---

### GET /api/agvs/reservation/resources/

**Response 200:**
```json
[
  {
    "id": 1,
    "resource_type": "crossroad",
    "resource_name": "CR-001",
    "created_at": "2025-11-27T10:00:00Z"
  }
]
```

## Error Handling

```python
from reservation import (
    BookingConflictError,       # 409
    ResourceNotFoundError,      # 404
    InvalidBookingError,        # 400
)

try:
    booking = booking_service.create_booking(request)
except BookingConflictError as e:
    # Slot is occupied - AGV must abort mission
    logger.error(f"Booking conflict: {e}")
    # Return to idle state, re-bid in auction
except ResourceNotFoundError as e:
    # Resource doesn't exist - configuration error
    logger.error(f"Resource not found: {e}")
    # Alert admin, check ResourceAgent table
except InvalidBookingError as e:
    # Invalid input (e.g., negative duration)
    logger.error(f"Invalid booking request: {e}")
    # Fix AGV's request parameters
```

## Value Object Usage

### TimeSlot

```python
from reservation import TimeSlot

# Create time slot
slot = TimeSlot(
    start_time=datetime(2025, 11, 27, 15, 30, 0),
    end_time=datetime(2025, 11, 27, 15, 30, 15)
)

# Check overlap
slot1 = TimeSlot(start_time=..., end_time=...)
slot2 = TimeSlot(start_time=..., end_time=...)
if slot1.overlaps_with(slot2):
    print("Conflict!")

# Immutable - cannot modify
# slot.start_time = ...  # ERROR: frozen dataclass
```

### BookingRequest

```python
from reservation import BookingRequest, TimeSlot

request = BookingRequest(
    resource_id=1,
    agv_id=2,
    time_slot=TimeSlot(
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=15)
    )
)

# Factory pattern - self-validating
# Invalid requests will raise InvalidBookingError at creation time
```

### SlotQuery

```python
from reservation import SlotQuery

query = SlotQuery(
    resource_id=1,
    requested_start_time=datetime.now(),
    duration=timedelta(seconds=15)
)

# Validates inputs at creation time
# Invalid queries raise InvalidBookingError immediately
```

## Testing Examples

### Unit Test (with mocked repositories)

```python
from unittest.mock import Mock
from reservation import SlotFinderService

def test_slot_finder_no_conflicts():
    # Mock repositories
    mock_resource_repo = Mock()
    mock_booking_repo = Mock()
    
    mock_resource_repo.find_by_id.return_value = Mock(id=1)
    mock_booking_repo.find_conflicting_bookings.return_value = []
    
    # Test service
    service = SlotFinderService(mock_resource_repo, mock_booking_repo)
    result = service.find_earliest_available_slot(query)
    
    assert result == query.requested_start_time
```

### Integration Test (with database)

```python
from django.test import TestCase
from reservation import BookingService, BookingRequest, TimeSlot
from agv_data.models import ResourceAgent, AGV

class BookingIntegrationTest(TestCase):
    def setUp(self):
        self.resource = ResourceAgent.objects.create(...)
        self.agv = AGV.objects.create(...)
        self.service = BookingService()
    
    def test_create_booking(self):
        request = BookingRequest(
            resource_id=self.resource.id,
            agv_id=self.agv.id,
            time_slot=TimeSlot(
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=15)
            )
        )
        
        booking = self.service.create_booking(request)
        self.assertIsNotNone(booking.id)
```

## Migration Path

### Step 1: Import new services

```python
# OLD
from agv_data import services

# NEW
from reservation import SlotFinderService, BookingService
```

### Step 2: Update function calls

```python
# OLD
earliest_start = services.find_earliest_available_slot(
    resource_id=resource_id,
    request_start_time=start_time,
    duration=duration
)

# NEW
slot_finder = SlotFinderService()
query = SlotQuery(
    resource_id=resource_id,
    requested_start_time=start_time,
    duration=duration
)
earliest_start = slot_finder.find_earliest_available_slot(query)
```

### Step 3: Update exception handling

```python
# OLD
except services.BookingConflictError as e:
    ...

# NEW
from reservation import BookingConflictError
except BookingConflictError as e:
    ...
```

## Architecture Layers

```
┌─────────────────────────────────────────┐
│          API Layer (views.py)           │  ← HTTP requests/responses
├─────────────────────────────────────────┤
│       Service Layer (services/)         │  ← Business logic orchestration
├─────────────────────────────────────────┤
│     Repository Layer (repositories/)    │  ← Database access
├─────────────────────────────────────────┤
│      Domain Layer (domain/)             │  ← Pure business logic
│  - Value Objects (immutable)            │
│  - Exceptions (custom errors)           │
└─────────────────────────────────────────┘
```

**Key Principles:**
- Upper layers depend on lower layers
- Lower layers are framework-independent
- Each layer has single responsibility
- Dependency injection for flexibility
