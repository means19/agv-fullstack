# Reservation Table Refactoring Summary

## Overview
Refactored the monolithic reservation table code into a clean, maintainable architecture following SOLID principles and design patterns.

## Architecture

```
reservation/
├── __init__.py                    # Module exports
├── domain/                        # Business logic (no framework dependencies)
│   ├── exceptions.py              # Custom exceptions hierarchy
│   └── value_objects.py           # Immutable domain objects
├── repositories/                  # Data access layer
│   ├── __init__.py
│   ├── resource_repository.py     # Resource CRUD + locking
│   └── booking_repository.py      # Booking CRUD + conflict detection
├── services/                      # Business operations
│   ├── __init__.py
│   ├── slot_finder_service.py     # Exploring Ant (find earliest slot)
│   └── booking_service.py         # Intention Ant (strict booking)
└── api/                           # HTTP interface
    ├── __init__.py
    ├── views.py                   # REST API views
    └── urls.py                    # URL routing
```

## Design Patterns Applied

### 1. **Repository Pattern**
- Separates data access from business logic
- Makes code testable (can mock repositories)
- Single source of truth for database operations

**Example:**
```python
# Before (mixed concerns)
resource = ResourceAgent.objects.get(id=resource_id)

# After (clean separation)
resource_repo = ResourceRepository()
resource = resource_repo.find_by_id(resource_id)
```

### 2. **Value Objects**
- Immutable domain objects (frozen dataclasses)
- Encapsulate business rules (e.g., TimeSlot overlap detection)
- Type-safe, self-validating

**Example:**
```python
# Before (primitive obsession)
def check_conflict(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

# After (rich domain model)
slot1 = TimeSlot(start_time=..., end_time=...)
slot2 = TimeSlot(start_time=..., end_time=...)
if slot1.overlaps_with(slot2):
    ...
```

### 3. **Dependency Injection**
- Services accept repository instances
- Easy to test (inject mocks)
- Flexible configuration

**Example:**
```python
# Can inject custom repositories for testing
slot_finder = SlotFinderService(
    resource_repo=MockResourceRepository(),
    booking_repo=MockBookingRepository()
)
```

### 4. **Single Responsibility Principle**
- Each class has ONE clear purpose
- ResourceRepository: Resource data access ONLY
- BookingRepository: Booking data access ONLY
- SlotFinderService: Slot finding logic ONLY
- BookingService: Booking creation logic ONLY

## Layer Responsibilities

### Domain Layer
**Pure business logic, no framework dependencies**

- `exceptions.py`: Custom exception hierarchy
  - `ReservationError` (base)
  - `BookingConflictError` (409 - auction integrity)
  - `ResourceNotFoundError` (404)
  - `InvalidBookingError` (400)

- `value_objects.py`: Immutable domain objects
  - `TimeSlot`: Time interval with overlap detection
  - `BookingRequest`: Factory pattern for booking creation
  - `SlotQuery`: Query parameters for slot search

### Repository Layer
**Database access abstraction**

- `resource_repository.py`: ResourceAgent operations
  - `find_by_id(lock=True/False)`: Get resource with optional SELECT FOR UPDATE
  - `exists()`: Check if resource exists

- `booking_repository.py`: Booking operations
  - `create()`: Create new booking
  - `find_conflicting_bookings()`: Find overlapping bookings
  - `has_conflict()`: Check if time slot is available
  - `find_by_agv()`: Get bookings for AGV
  - `find_by_resource()`: Get bookings for resource
  - `delete()`: Cancel booking
  - `delete_by_agv()`: Bulk cancel AGV bookings

### Service Layer
**Business operations orchestration**

- `slot_finder_service.py`: **Exploring Ant phase**
  - `find_earliest_available_slot()`: Iterative slot search
  - Returns earliest time when resource is free
  - Uses transaction management for consistency

- `booking_service.py`: **Intention Ant phase**
  - `create_booking()`: **STRICT MODE** - book exact slot or fail
  - `cancel_booking()`: Cancel specific booking
  - `cancel_agv_bookings()`: Bulk cancel for AGV
  - `get_agv_bookings()`: List AGV's bookings
  - `get_resource_bookings()`: List resource's bookings

### API Layer
**HTTP interface**

- `views.py`: REST API views
  - `QuerySlotView` (POST): Exploring Ant endpoint
  - `BookSlotView` (POST): Intention Ant endpoint (strict)
  - `ListBookingsView` (GET): List bookings with filters
  - `CancelBookingView` (DELETE): Cancel booking
  - `ListResourcesView` (GET): List all resources

## Critical Design Decision: Strict Booking Mode

The `BookingService.create_booking()` method implements **strict/fail-fast** approach:

```python
@transaction.atomic
def create_booking(self, request: BookingRequest) -> Booking:
    """
    CRITICAL: Books the EXACT slot or fails with 409.
    
    Why this is critical for SSI-DMAS:
    - AGV bids based on specific slot from Exploring Ant
    - Intention Ant MUST get that exact slot or fail
    - Auto-serialization would break auction integrity
      (AGV wins for slot A but gets slot B with different cost)
    """
    # Lock resource to prevent race conditions
    self.resource_repo.find_by_id(request.resource_id, lock=True)
    
    # Check for conflicts with locking
    if self.booking_repo.has_conflict(
        resource_id=request.resource_id,
        time_slot=request.time_slot,
        lock=True
    ):
        raise BookingConflictError(
            f"Exact time slot is already occupied. "
            f"Auction result is invalid. AGV must re-bid."
        )
    
    # No conflict! Create booking
    return self.booking_repo.create(...)
```

**Why no auto-serialization?**
- Exploring Ant finds slot at T1, estimates cost C1
- AGV bids C1 in auction and wins
- If Intention Ant books at T2 (auto-serialized), actual cost is C2 ≠ C1
- This breaks auction integrity!

**Solution:** Return 409 Conflict, force AGV to abort mission and re-bid.

## Migration Guide

### Option 1: Drop-in Replacement (Recommended)

Update `agv_data/views.py` to use new services:

```python
# OLD (agv_data/views.py)
from . import services

class QuerySlotView(APIView):
    def post(self, request, resource_id):
        earliest_slot_start = services.find_earliest_available_slot(
            resource_id=resource_id,
            request_start_time=start_time,
            duration=duration
        )

# NEW (agv_data/views.py) 
from reservation import SlotFinderService
from reservation.domain.value_objects import SlotQuery

class QuerySlotView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slot_finder = SlotFinderService()
    
    def post(self, request, resource_id):
        query = SlotQuery(
            resource_id=resource_id,
            requested_start_time=start_time,
            duration=duration
        )
        earliest_slot_start = self.slot_finder.find_earliest_available_slot(query)
```

### Option 2: Use New API Views (Clean Slate)

Replace old views with new ones in URL routing:

```python
# OLD (agv_data/urls.py)
from agv_data.views import QuerySlotView, BookSlotView, ...

urlpatterns = [
    path('reservation/resource/<int:resource_id>/query_slot/', QuerySlotView.as_view()),
    ...
]

# NEW (agv_server/urls.py or agv_data/urls.py)
from reservation.api import urls as reservation_urls

urlpatterns = [
    path('api/agvs/reservation/', include(reservation_urls)),
    ...
]
```

## Usage Examples

### Direct Service Usage (for testing or internal use)

```python
from datetime import datetime, timedelta
from reservation import (
    SlotFinderService,
    BookingService,
    SlotQuery,
    BookingRequest,
    TimeSlot,
    BookingConflictError
)

# Exploring Ant: Find earliest available slot
slot_finder = SlotFinderService()
query = SlotQuery(
    resource_id=1,
    requested_start_time=datetime.now(),
    duration=timedelta(seconds=15)
)
earliest_start = slot_finder.find_earliest_available_slot(query)

# Intention Ant: Book the exact slot
booking_service = BookingService()
try:
    booking_request = BookingRequest(
        resource_id=1,
        agv_id=2,
        time_slot=TimeSlot(
            start_time=earliest_start,
            end_time=earliest_start + timedelta(seconds=15)
        )
    )
    booking = booking_service.create_booking(booking_request)
    print(f"Booking created: {booking.id}")
except BookingConflictError as e:
    print(f"Conflict! AGV must abort: {e}")
```

### API Usage (from frontend or AGV clients)

```bash
# 1. Exploring Ant: Query earliest slot
curl -X POST http://localhost:8000/api/agvs/reservation/resource/1/query_slot/ \
  -H "Content-Type: application/json" \
  -d '{
    "request_start_time": "2025-11-27T15:30:00Z",
    "duration_seconds": 15
  }'

# Response:
# {
#   "resource_id": 1,
#   "earliest_available_start": "2025-11-27T15:30:00Z",
#   "requested_duration_seconds": 15,
#   "calculated_delay_seconds": 0
# }

# 2. Intention Ant: Book the exact slot
curl -X POST http://localhost:8000/api/agvs/reservation/resource/1/book_slot/ \
  -H "Content-Type: application/json" \
  -d '{
    "agv_id": 2,
    "request_start_time": "2025-11-27T15:30:00Z",
    "duration_seconds": 15
  }'

# Response 201 (success):
# {
#   "id": 123,
#   "resource_id": 1,
#   "agv_id": 2,
#   "start_time": "2025-11-27T15:30:00Z",
#   "end_time": "2025-11-27T15:30:15Z",
#   "created_at": "..."
# }

# Response 409 (conflict - AGV must abort):
# {
#   "error": "Exact time slot ... is already occupied. Auction result is invalid. AGV must re-bid."
# }
```

## Testing Strategy

### Unit Tests (for each layer)

```python
# Domain layer tests
def test_timeslot_overlap():
    slot1 = TimeSlot(start_time=..., end_time=...)
    slot2 = TimeSlot(start_time=..., end_time=...)
    assert slot1.overlaps_with(slot2)

# Repository layer tests (with database)
def test_booking_repository_conflict_detection():
    repo = BookingRepository()
    # Create booking
    # Check conflict
    assert repo.has_conflict(...)

# Service layer tests (with mocked repositories)
def test_slot_finder_service():
    mock_resource_repo = Mock()
    mock_booking_repo = Mock()
    service = SlotFinderService(mock_resource_repo, mock_booking_repo)
    # Test logic without database
```

### Integration Tests

```python
# Test full flow
def test_exploring_then_intention_ant():
    # Query slot
    response1 = client.post('/api/agvs/reservation/resource/1/query_slot/', ...)
    earliest_start = response1.data['earliest_available_start']
    
    # Book that exact slot
    response2 = client.post('/api/agvs/reservation/resource/1/book_slot/', {
        'agv_id': 2,
        'request_start_time': earliest_start,
        'duration_seconds': 15
    })
    assert response2.status_code == 201
```

## Benefits of This Architecture

1. **Testability**
   - Pure functions in domain layer (no side effects)
   - Mocked repositories for service tests
   - Integration tests for API layer

2. **Maintainability**
   - Clear separation of concerns
   - Each file has single purpose
   - Easy to locate and fix bugs

3. **Extensibility**
   - Add new services without touching existing ones
   - Swap repository implementations (e.g., cache layer)
   - Add new API endpoints easily

4. **Type Safety**
   - Value objects catch errors at creation time
   - IDEs provide better autocomplete
   - Reduced runtime errors

5. **Documentation**
   - Code is self-documenting (clear structure)
   - Business rules in domain layer (visible)
   - API contracts in views (explicit)

## Next Steps

1. **Update existing code** to use new services
   - Replace `agv_data.services` calls with `reservation` imports
   - Update tests to use new structure

2. **Update URL routing** 
   - Option A: Keep old URLs, update views to use new services
   - Option B: Create new URLs under `/api/agvs/reservation/`

3. **Add comprehensive tests**
   - Unit tests for each layer
   - Integration tests for services
   - API tests for endpoints

4. **Update documentation**
   - Add architecture diagram
   - Update quickstart guide
   - Document migration path

5. **Deprecate old code** (gradually)
   - Mark `agv_data.services` functions as deprecated
   - Add warnings in logs
   - Remove after migration is complete
