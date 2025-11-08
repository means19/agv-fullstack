# Reservation Table Documentation

## Overview

The **Reservation Table** is a critical component of the D-MAS (Delegate Multi-Agent System) architecture that manages time-based reservations for shared resources in the AGV system. It ensures conflict-free resource allocation through strict booking policies and transaction isolation.

**Location:** `agv_server/agv_data/`

## Core Concept

In an AGV warehouse system:
- **Resources**: Crossroad Agents (CA) and Logical Segment Agents (LSA)
- **Bookings**: Time-based reservations made by AGVs
- **Conflict Prevention**: Only one AGV can use a resource at any given time
- **Auction Integrity**: Strict/fail-fast approach ensures AGVs get exactly what they bid for

## Architecture

### Two-Agent System

1. **Exploring Ant (Query Phase)**
   - Calls `query_slot` API to find earliest available time
   - Does NOT make reservations
   - Used for cost calculation and route planning

2. **Intention Ant (Booking Phase)**
   - Calls `book_slot` API to reserve exact time slot
   - Returns 409 Conflict if slot is occupied
   - AGV must abort mission or replan on conflict

### Database Models

#### ResourceAgent Model

Represents a shared resource (CA or LSA).

```python
class ResourceAgent(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('CA', 'Crossroad Agent'),
        ('LSA', 'Logical Segment Agent'),
    ]
    
    resource_id = models.IntegerField(unique=True, primary_key=True)
    resource_type = models.CharField(max_length=3, choices=RESOURCE_TYPE_CHOICES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Fields:**
- `resource_id`: Unique identifier (e.g., node 1, segment 5)
- `resource_type`: Either 'CA' or 'LSA'
- `description`: Optional notes about the resource
- `created_at`: Timestamp when resource was created

#### Booking Model

Represents a time-based reservation.

```python
class Booking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    resource = models.ForeignKey(ResourceAgent, on_delete=models.CASCADE)
    agv_id = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['resource', 'start_time']),
            models.Index(fields=['resource', 'end_time']),
        ]
```

**Fields:**
- `booking_id`: Auto-incrementing primary key
- `resource`: Foreign key to ResourceAgent
- `agv_id`: Which AGV owns this booking
- `start_time`: When the reservation starts (timezone-aware UTC)
- `end_time`: When the reservation ends (timezone-aware UTC)
- `created_at`: Timestamp of booking creation

**Indexes:**
- `(resource, start_time)`: Fast lookup for conflict detection
- `(resource, end_time)`: Fast lookup for cleanup queries

### Conflict Detection

Two bookings conflict if they overlap in time:

```python
def has_overlap(booking1, booking2):
    """
    Returns True if two bookings overlap.
    
    Overlap occurs if:
    - booking1.start < booking2.end AND
    - booking1.end > booking2.start
    """
    return (booking1.start_time < booking2.end_time and 
            booking1.end_time > booking2.start_time)
```

**Example:**
```
Booking A: [10:00 - 10:30]
Booking B: [10:20 - 10:50]
→ CONFLICT (overlaps from 10:20 to 10:30)

Booking A: [10:00 - 10:30]
Booking C: [10:30 - 11:00]
→ NO CONFLICT (adjacent but not overlapping)
```

## API Endpoints

### 1. Query Slot (Exploring Ant)

Find the earliest available time slot for a resource.

**Endpoint:** `POST /api/agvs/reservation/resource/{resource_id}/query_slot/`

**Request:**
```json
{
    "request_start_time": "2025-11-08T10:00:00Z",
    "duration_seconds": 30
}
```

**Response (No Conflict):**
```json
{
    "resource_id": 1,
    "earliest_available_start": "2025-11-08T10:00:00Z",
    "requested_duration_seconds": 30,
    "calculated_delay_seconds": 0.0
}
```

**Response (Conflict):**
```json
{
    "resource_id": 1,
    "earliest_available_start": "2025-11-08T10:45:00Z",
    "requested_duration_seconds": 30,
    "calculated_delay_seconds": 2700.0
}
```

**Business Logic:**
1. Lock resource with `select_for_update()`
2. Get all existing bookings for the resource
3. Start from `request_start_time`
4. Check if current slot is available
5. If conflict, move to end of conflicting booking
6. Repeat until free slot found
7. Return earliest available start time

**Use Case:**
- Exploring Ant queries this to calculate wait energy and tardiness
- Does NOT create a booking
- Multiple AGVs can query simultaneously

### 2. Book Slot (Intention Ant)

Create a reservation for a specific time slot.

**Endpoint:** `POST /api/agvs/reservation/resource/{resource_id}/book_slot/`

**Request:**
```json
{
    "agv_id": 2,
    "request_start_time": "2025-11-08T10:00:00Z",
    "duration_seconds": 30
}
```

**Response (Success - 201 Created):**
```json
{
    "booking_id": 123,
    "resource_id": 1,
    "resource_info": {
        "resource_id": 1,
        "resource_type": "CA",
        "description": "Main crossroad"
    },
    "agv_id": 2,
    "start_time": "2025-11-08T10:00:00Z",
    "end_time": "2025-11-08T10:00:30Z",
    "created_at": "2025-11-08T09:55:00Z"
}
```

**Response (Conflict - 409 Conflict):**
```json
{
    "error": "Booking conflict (retry recommended): The requested time slot [2025-11-08T10:00:00Z to 2025-11-08T10:00:30Z] is already booked."
}
```

**Business Logic (STRICT MODE):**
1. Lock resource with `select_for_update()`
2. Check if EXACT requested slot is available
3. If ANY conflict: Return 409 Conflict
4. If available: Create booking and return 201
5. AGV must handle conflict (abort or replan)

**Use Case:**
- Intention Ant calls this after Exploring Ant found acceptable cost
- Books the EXACT slot from exploration
- If 409: Another AGV booked first, mission fails

### 3. List Bookings

List all bookings for an AGV or a resource.

**Endpoint:** `GET /api/agvs/reservation/bookings/?agv_id={agv_id}`  
**Endpoint:** `GET /api/agvs/reservation/bookings/?resource_id={resource_id}`

**Query Parameters:**
- `agv_id`: Filter by AGV (optional)
- `resource_id`: Filter by resource (optional)
- `include_past`: Include past bookings (default: false)

**Response:**
```json
[
    {
        "booking_id": 123,
        "resource_id": 1,
        "resource_info": {
            "resource_id": 1,
            "resource_type": "CA",
            "description": "Main crossroad"
        },
        "agv_id": 2,
        "start_time": "2025-11-08T10:00:00Z",
        "end_time": "2025-11-08T10:00:30Z",
        "created_at": "2025-11-08T09:55:00Z"
    }
]
```

### 4. Cancel Booking

Cancel a specific booking.

**Endpoint:** `DELETE /api/agvs/reservation/bookings/{booking_id}/`

**Response (Success - 200 OK):**
```json
{
    "message": "Booking 123 cancelled successfully"
}
```

**Response (Not Found - 404):**
```json
{
    "error": "Booking 123 not found"
}
```

### 5. List Resources

List all available resources.

**Endpoint:** `GET /api/agvs/reservation/resources/`

**Response:**
```json
[
    {
        "resource_id": 1,
        "resource_type": "CA",
        "description": "Main crossroad",
        "created_at": "2025-11-01T00:00:00Z"
    },
    {
        "resource_id": 2,
        "resource_type": "LSA",
        "description": "Segment A to B",
        "created_at": "2025-11-01T00:00:00Z"
    }
]
```

## Service Layer

Business logic is separated into `agv_data/services.py`:

### find_earliest_available_slot()

```python
def find_earliest_available_slot(
    resource_id: int,
    request_start_time: datetime,
    duration: timedelta
) -> datetime:
    """
    Find earliest available time slot for a resource.
    
    Uses iterative algorithm to find first non-conflicting slot.
    Returns start time (may be later than requested).
    """
```

**Algorithm:**
1. Lock resource row
2. Get all bookings sorted by start_time
3. candidate_start = request_start_time
4. For each booking:
   - If booking ends before candidate: skip
   - If booking starts after candidate + duration: slot is free, return
   - Else: conflict, move candidate to booking.end_time
5. If no conflicts: return candidate_start

### create_booking()

```python
def create_booking(
    resource_id: int,
    agv_id: int,
    exact_start_time: datetime,
    duration: timedelta
) -> Booking:
    """
    Create booking for EXACT time slot (strict mode).
    
    Raises BookingConflictError if ANY overlap exists.
    This ensures auction integrity.
    """
```

**Algorithm:**
1. Lock resource and bookings
2. Check for ANY overlap with exact slot
3. If conflict: raise BookingConflictError
4. Else: create and save booking

### Other Functions

- `get_bookings_for_agv(agv_id, include_past=False)`: Get AGV's bookings
- `get_bookings_for_resource(resource_id)`: Get resource's bookings
- `cancel_booking(booking_id)`: Cancel specific booking
- `cancel_agv_bookings(agv_id)`: Cancel all bookings for an AGV

## Transaction Isolation

### Row-Level Locking

All service functions use `select_for_update()`:

```python
with transaction.atomic():
    resource = ResourceAgent.objects.select_for_update().get(
        resource_id=resource_id
    )
    
    existing_bookings = Booking.objects.select_for_update().filter(
        resource=resource
    )
    
    # ... business logic ...
```

**Benefits:**
- Prevents race conditions
- Ensures only one transaction can modify resource at a time
- Other transactions wait until lock is released

### Strict/Fail-Fast Approach

**Why not auto-serialize (queue all bookings)?**

In a D-MAS auction system:
1. AGV explores route and finds cost (e.g., "arrive at 10:00, cost = 50")
2. AGV bids based on this cost
3. AGV wins auction
4. **Intention Ant MUST get exact slot from exploration**
5. If slot changed (queued to 10:30), cost changes, auction invalid!

**Solution: Strict booking**
- Book EXACT slot or fail with 409
- AGV handles failure (abort mission or replan)
- Auction integrity preserved

## Admin Interface

Django admin provides web interface for managing resources and bookings:

**ResourceAgent Admin:**
- List display: resource_id, resource_type, description, created_at
- Search: resource_id, description
- Filters: resource_type, created_at

**Booking Admin:**
- List display: booking_id, resource, agv_id, start_time, end_time, created_at
- Search: booking_id, agv_id
- Filters: resource, created_at
- Date hierarchy: created_at

**Access:** `http://localhost:8000/admin/agv_data/`

## Management Commands

### Cleanup Old Bookings

```bash
# Delete bookings older than 7 days (default)
python manage.py cleanup_bookings

# Delete bookings older than 30 days
python manage.py cleanup_bookings --days 30

# Dry run (show what would be deleted)
python manage.py cleanup_bookings --dry-run
```

**Use Case:**
- Prevent database bloat
- Remove historical data
- Run as cron job for maintenance

## Testing

### Test Suite Location

`tests/test_reservation_table.py` - Sequential functional tests  
`tests/test_concurrent_booking.py` - Concurrency and race condition tests  
`tests/check_overlaps.py` - Overlap detection verification

### Running Tests

```bash
cd tests

# Sequential tests (9 scenarios)
python test_reservation_table.py

# Concurrent tests (race condition)
python test_concurrent_booking.py

# Check for overlaps
python check_overlaps.py
```

### Test Coverage

**Sequential Tests:**
1. ✅ Query available slot (no conflicts)
2. ✅ Query with existing booking (should delay)
3. ✅ Book available slot
4. ✅ Book occupied slot (should fail with 409)
5. ✅ List bookings by AGV
6. ✅ List bookings by resource
7. ✅ Cancel booking
8. ✅ List all resources
9. ✅ Invalid resource (404)

**Concurrent Tests:**
- 10 threads try to book same slot simultaneously
- Expected: 1 success, 9 failures (409 Conflict)
- Validates transaction isolation and locking

**Overlap Check:**
- Fetches all bookings
- Checks every pair for time overlap
- Expected: Zero overlaps

## Sample Data

### Create Sample Resources

```python
# agv_server/create_sample_resources.py
from agv_data.models import ResourceAgent

# Create 10 CA resources
for i in range(1, 11):
    ResourceAgent.objects.get_or_create(
        resource_id=i,
        defaults={
            'resource_type': 'CA',
            'description': f'Crossroad Agent {i}'
        }
    )

# Create 10 LSA resources
for i in range(11, 21):
    ResourceAgent.objects.get_or_create(
        resource_id=i,
        defaults={
            'resource_type': 'LSA',
            'description': f'Logical Segment Agent {i}'
        }
    )
```

**Run:**
```bash
docker compose exec django_app python create_sample_resources.py
```

## Integration with D-MAS

### Complete Flow

1. **AGV receives order**
   - Order has pickup/dropoff locations and deadlines

2. **Pathfinding**
   - Calculate route from current location to pickup to dropoff
   - Route consists of resources (CAs and LSAs)

3. **Exploring Ant (Cost Calculation)**
   - For each step in route:
     - Call `query_slot` API
     - Calculate energy (travel + wait)
     - Track tardiness
   - Return total cost J

4. **Auction/Decision**
   - Compare costs of different routes/AGVs
   - Select best option
   - AGV wins auction

5. **Intention Ant (Booking)**
   - For each step in winning route:
     - Call `book_slot` API with EXACT times from exploration
     - If 409 Conflict: Abort mission (another AGV won)
     - If 201 Created: Proceed to next step
   - If all bookings succeed: Execute route

6. **Execution**
   - AGV follows booked route
   - Arrives at each resource at booked time
   - Releases resource after use

7. **Completion/Cancellation**
   - On success: Bookings naturally expire
   - On failure: Call cancel API to free resources

## Best Practices

### For AGV Developers

1. **Always query before booking**
   - Exploring Ant → calculate cost
   - Intention Ant → book only if acceptable

2. **Handle 409 Conflicts gracefully**
   - Replan route
   - Bid on different order
   - Return to parking

3. **Cancel bookings on abort**
   - Free resources for other AGVs
   - Prevent resource starvation

4. **Use timezone-aware datetimes**
   - All times in UTC
   - Convert to local time only for display

### For System Operators

1. **Monitor booking patterns**
   - High conflict rates may indicate:
     - Too many AGVs
     - Poor route planning
     - Hotspot resources

2. **Run cleanup regularly**
   - Prevent database bloat
   - Schedule daily cron job

3. **Index optimization**
   - Existing indexes cover most queries
   - Monitor slow queries and add indexes if needed

4. **Backup strategy**
   - Bookings are transient (expire quickly)
   - ResourceAgent data is critical (backup required)

## Performance Considerations

### Database Queries

**Optimized:**
- Indexed lookups on `(resource, start_time)` and `(resource, end_time)`
- `select_for_update()` on minimal rows
- Filtered queries (only future bookings)

**Potential Issues:**
- Many concurrent bookings on same resource
- Long-running transactions holding locks

**Solutions:**
- Keep transactions short
- Release locks ASAP
- Use connection pooling

### API Response Times

**Typical:**
- `query_slot`: 50-200ms (depends on booking count)
- `book_slot`: 100-300ms (includes conflict check)
- `list_bookings`: 20-100ms (depends on result count)

**Optimization:**
- Database indexes (already implemented)
- Query result caching (if needed)
- Pagination for large result sets

## Troubleshooting

### Issue: 409 Conflict on every booking

**Diagnosis:**
- Check if slot is actually occupied
- Verify timezone consistency
- Check for clock skew between clients

**Solution:**
```bash
# List all bookings for resource
curl "http://localhost:8000/api/agvs/reservation/bookings/?resource_id=1"

# Check for overlaps
python tests/check_overlaps.py
```

### Issue: Query returns far future time

**Diagnosis:**
- Resource heavily booked
- Long-duration bookings
- Many AGVs competing

**Solution:**
- Use alternative routes
- Increase resource capacity
- Reduce AGV count

### Issue: Database locked

**Diagnosis:**
- Long-running transaction
- Deadlock situation
- Too many concurrent requests

**Solution:**
```bash
# Check active connections
docker compose exec db psql -U postgres -d agv_db -c "SELECT * FROM pg_stat_activity;"

# Kill long-running queries
docker compose exec db psql -U postgres -d agv_db -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';"
```

## Configuration

### Settings (settings.py)

```python
# Timezone (IMPORTANT)
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_TZ = True  # Must be True for timezone-aware datetimes

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... connection settings
    }
}
```

### Environment Variables

```bash
# API base URL (for clients)
RESERVATION_API_URL=http://localhost:8000/api/agvs/reservation

# Database connection
DATABASE_URL=postgresql://user:pass@localhost:5432/agv_db
```

## Migration History

```bash
# Initial models
python manage.py makemigrations agv_data

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations agv_data
```

**Migration Files:**
- `0001_initial.py`: ResourceAgent and Booking models
- Future migrations as schema evolves

## Security Considerations

### Authentication (Future)

Currently no authentication required (development mode).

**Production Requirements:**
- API key authentication
- JWT tokens
- Role-based access control (RBAC)

### Authorization (Future)

- AGVs can only cancel their own bookings
- Admin users can cancel any booking
- Read-only users can only query

### Rate Limiting (Future)

- Prevent DOS attacks
- Limit queries per AGV per minute
- Throttle booking attempts

## Monitoring

### Metrics to Track

1. **Booking Success Rate**
   - `201 Created` / Total booking attempts
   - Low rate indicates resource contention

2. **Query Delay Average**
   - Average `calculated_delay_seconds`
   - High values indicate congestion

3. **Conflict Rate**
   - `409 Conflict` / Total booking attempts
   - High rate indicates poor coordination

4. **API Response Times**
   - P50, P95, P99 latencies
   - Identify slow endpoints

### Logging

All service functions log key events:
- Resource not found
- Booking conflicts
- Successful bookings
- Cancellations

**Log Location:** Check Django logs or container logs
```bash
docker compose logs -f django_app | grep -i booking
```

## Future Enhancements

### Priority Bookings
- Emergency AGVs get priority
- Regular AGVs wait for high-priority

### Reservation Extensions
- Allow extending booking duration
- Update end_time without canceling

### Booking Transfers
- Transfer booking from one AGV to another
- Useful for AGV failures

### Predictive Allocation
- Machine learning to predict congestion
- Proactive route planning

### Multi-Resource Bookings
- Atomic booking of multiple resources
- All-or-nothing reservation

## References

- **D-MAS Specification:** `docs/agv_agent_logic.md`
- **Exploring Ant Implementation:** `docs/agv-agent-exploring-ant.md`
- **Quick Start Guide:** `docs/agv-agent-quickstart.md`
- **Implementation Summary:** `docs/agv-agent-implementation-summary.md`

## Related Documentation
- [Quick Start Guide](./reservation-table-quickstart.md)
- [Implementation Summary](./reservation-table-implementation-summary.md)

## See also
- [AGV Agent Logic (Exploring Ant)](/docs/exploring-ants/agv-agent-exploring-ant.md)
---
