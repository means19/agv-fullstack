# AGV Agent Logic (Exploring Ant - DMAS-ET)

## Overview

The AGV Agent Logic implements the **Exploring Ant (DMAS-ET)** algorithm for the Delegate Multi-Agent System (D-MAS). This algorithm simulates an AGV's journey through a planned route, queries the Reservation Table for resource availability, and calculates the total cost based on energy consumption and tardiness.

**Location:** `agv_server/agv_data/agv_agent.py`

## Core Concept

In the D-MAS architecture:
- **Exploring Ant**: Simulates a journey virtually, queries resource availability, calculates cost
- **Intention Ant**: (Future) Books resources if Exploring Ant's cost is acceptable
- **Resource Agents**: CAs (Crossroad Agents) and LSAs (Logical Segment Agents) manage reservations via Reservation Table

## Algorithm Flow

```
1. Input: route_plan (list of RouteStep), global_start_time
2. For each step in route_plan:
   a. Query Reservation Table API for earliest available slot
   b. Calculate delay (if any)
   c. Calculate wait energy (idle power during delay)
   d. Calculate travel energy (based on distance and load)
   e. Update current time
   f. Check tardiness if this is a task endpoint
3. Calculate total cost J = K_ENERGY * energy + K_TARDINESS * tardiness
4. Return cost J (or inf if any API fails)
```

## Key Components

### RouteStep Class

Represents one step in an AGV's planned route.

```python
RouteStep(
    resource_id=1,          # ID of resource (CA or LSA)
    distance_m=50.0,        # Distance to travel in meters
    duration_sec=30.0,      # Time to complete this step in seconds
    load_kg=100.0,          # Load weight in kilograms
    is_task_endpoint=False, # Whether this is a pickup/dropoff point
    due_date=None           # Deadline (if task endpoint)
)
```

### DMAS_ET Function

Main function that simulates the journey and calculates cost.

**Signature:**
```python
def DMAS_ET(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> float
```

**Parameters:**
- `route_plan`: List of RouteStep objects
- `global_start_time`: When the journey should start
- `agv_id`: Identifier for logging

**Returns:**
- Total cost J (float)
- `float('inf')` if route is invalid or API fails

## Energy Calculations

### Travel Energy

Formula: `E_travel = (C_BASE + C_LOAD_COEFF * load_kg) * distance_m`

**Constants:**
- `C_BASE = 0.05` kJ/m (base energy per meter)
- `C_LOAD_COEFF = 0.002` kJ/(kg·m) (additional energy per kg per meter)

**Example:** 100kg load over 50m
```
E_travel = (0.05 + 0.002 * 100) * 50
         = (0.05 + 0.2) * 50
         = 12.5 kJ
```

### Wait Energy

Formula: `E_wait = P_IDLE * delay_sec / 1000`

**Constants:**
- `P_IDLE = 0.1` W (watts - idle power consumption)

**Example:** 60 second delay
```
E_wait = 0.1 * 60 / 1000
       = 6 / 1000
       = 0.006 kJ

Breakdown:
  0.1 W × 60 s = 6 J (watts × seconds = joules)
  6 J ÷ 1000 = 0.006 kJ (convert joules to kilojoules)
```

### Total Cost

Formula: `J = K_ENERGY * total_energy_kJ + K_TARDINESS * total_tardiness_sec`

**Constants:**
- `K_ENERGY = 0.5` (weight for energy component)
- `K_TARDINESS = 0.5` (weight for tardiness component)

**Example:** 50 kJ energy, 120 sec tardiness
```
J = 0.5 * 50 + 0.5 * 120
  = 25 + 60
  = 85
```

## API Integration

The Exploring Ant queries the Reservation Table API for each step:

**Endpoint:** `POST /api/agvs/reservation/resource/{resource_id}/query_slot/`

**Request:**
```json
{
    "request_start_time": "2025-11-08T06:30:00Z",
    "duration_seconds": 30
}
```

**Response:**
```json
{
    "resource_id": 1,
    "earliest_available_start": "2025-11-08T06:30:00Z",
    "requested_duration_seconds": 30,
    "calculated_delay_seconds": 0.0
}
```

If the earliest available start is later than the desired start, the AGV must wait (incurring wait energy and potential tardiness).

## Usage Example

```python
from datetime import datetime, timedelta, timezone
from agv_data.agv_agent import RouteStep, DMAS_ET

# Define route plan
route_plan = [
    RouteStep(
        resource_id=1,
        distance_m=50.0,
        duration_sec=30.0,
        load_kg=0.0,  # Empty AGV
        is_task_endpoint=False
    ),
    RouteStep(
        resource_id=2,
        distance_m=10.0,
        duration_sec=20.0,
        load_kg=200.0,  # Picked up item
        is_task_endpoint=True,
        due_date=datetime.now(timezone.utc) + timedelta(minutes=5)
    ),
    RouteStep(
        resource_id=3,
        distance_m=100.0,
        duration_sec=60.0,
        load_kg=200.0,  # Still carrying item
        is_task_endpoint=False
    ),
    RouteStep(
        resource_id=4,
        distance_m=10.0,
        duration_sec=20.0,
        load_kg=0.0,  # Dropped off item
        is_task_endpoint=True,
        due_date=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
]

# Run Exploring Ant
start_time = datetime.now(timezone.utc)
cost = DMAS_ET(route_plan, start_time, agv_id="AGV_1")

if cost == float('inf'):
    print("Route is invalid or API failed")
else:
    print(f"Total cost: {cost}")
```

## Testing

Run the test suite:
```bash
cd tests
python test_agv_agent.py
```

**Test Coverage:**
1. ✅ Energy calculation functions
2. ✅ Simple route (no conflicts, no tardiness)
3. ✅ Route with task endpoints and tardiness
4. ✅ Route with varying loads (pickup/dropoff)
5. ✅ Invalid routes (empty, invalid resource)

## Silent Mode

For performance testing or batch processing, use `DMAS_ET_silent()` which has identical logic but no console output:

```python
from agv_data.agv_agent import DMAS_ET_silent

cost = DMAS_ET_silent(route_plan, start_time, agv_id="AGV_1")
```

## Next Steps

1. **Intention Ant**: When Exploring Ant returns acceptable cost, Intention Ant books the exact slots
2. **Sequential Single Item**: Implement auction mechanism for order selection
3. **Multi-Agent Coordination**: Handle conflicts when multiple AGVs explore same resources

## Configuration

All constants are defined in `agv_data/agv_agent_constants.py`:
- Energy weights: `K_ENERGY`, `K_TARDINESS`
- Energy parameters: `C_BASE`, `C_LOAD_COEFF`, `P_IDLE`
- API configuration: `RESERVATION_API_URL`

To modify constants, edit `agv_agent_constants.py` and restart the application.

## Tardiness Handling

Tardiness is calculated only for steps marked as `is_task_endpoint=True`:

- If `finish_time > due_date`: `tardiness = (finish_time - due_date).total_seconds()`
- Otherwise: `tardiness = 0`

Total tardiness is the sum across all task endpoints.

## Error Handling

DMAS_ET returns `float('inf')` in these cases:
- Route plan is empty
- Any API call fails (network error, server error)
- Invalid API response (missing fields)
- Resource not found (404)

This allows the calling code to reject the route and try alternatives.

## Performance Considerations

- Each RouteStep makes one API call
- API calls are synchronous (sequential)
- For 10-step route: ~1-2 seconds total (depends on server response time)
- Consider parallel exploration for multiple route alternatives

## Verbose Output Example

```
[DMAS-ET] TEST_AGV_1 starting exploration at 2025-11-08 06:28:42+00:00
[DMAS-ET] Route has 3 steps

--- Step 1/3 ---
Resource ID: 1
Distance: 50.0m, Duration: 30.0s
Load: 100.0kg, Task endpoint: False
Desired start: 2025-11-08 06:28:42+00:00
Earliest available: 2025-11-08 06:28:42+00:00
No delay
Travel energy: 12.500000 kJ
Finish time: 2025-11-08 06:29:12+00:00

============================================================
[DMAS-ET] TEST_AGV_1 Exploration Complete
============================================================
Total Energy: 56.250000 kJ
Total Tardiness: 0.00 seconds
Cost J = 0.5 * 56.250000 + 0.5 * 0.00
Cost J = 28.125000
============================================================
```

## Related Documentation
- [Quick Start Guide](./agv-agent-quickstart.md)
- [Implementation Summary](./agv-agent-implementation-summary.md)

## See also
- [Reservation Table](/docs/reservation-table/reservation-table.md)