# AGV Agent Logic (Exploring Ant - DMAS-ET)

## Overview

The AGV Agent Logic implements the **Exploring Ant (DMAS-ET)** algorithm for the Delegate Multi-Agent System (D-MAS). This algorithm simulates an AGV's journey through a planned route, queries the Reservation Table for resource availability, and calculates **raw costs** (energy and Total Flow Time) without normalization.

**Location:** `agv_server/agv_data/agv_agent.py`

**⚠️ Important Change (v2.0):**
- **Metric**: Sum of Tardiness (SOT) → **Total Flow Time (TFT)**
- **Return Type**: `float` (cost J) → **`Tuple[float, float]`** (energy, TFT)
- **Normalization**: Moved from DMAS-ET to **bidding layer** (Dynamic Baseline Normalization)

See [TFT + Dynamic Normalization Documentation](../tft-dynamic-normalization.md) for details.

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
   f. Track TFT (Total Flow Time) if this is a task endpoint
3. Return RAW costs: (total_energy_kj, total_tft_sec)
   - NO normalization applied
   - NO K_ENERGY/K_TIME weighting applied
   - Bidding layer handles normalization and final cost calculation
4. Return (inf, inf) if any API fails
```

**Key Change**: Algorithm now returns **raw values** instead of weighted cost J. This allows the bidding layer to apply **Dynamic Baseline Normalization** for fair comparison across different tasks.

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

Main function that simulates the journey and calculates **raw costs**.

**Signature:**
```python
def DMAS_ET(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> Tuple[float, float]
```

**Parameters:**
- `route_plan`: List of RouteStep objects
- `global_start_time`: When the journey should start
- `agv_id`: Identifier for logging

**Returns:**
- `Tuple[float, float]`: **(total_energy_kj, total_tft_sec)**
- `(float('inf'), float('inf'))` if route is invalid or API fails

**⚠️ Breaking Change**: Return type changed from `float` → `Tuple[float, float]`
- Before: `cost = DMAS_ET(route, start_time)`
- After: `energy, tft = DMAS_ET(route, start_time)`

### DMAS_ET_silent Function

Silent version (no console output) - same signature and behavior as `DMAS_ET`.

```python
def DMAS_ET_silent(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> Tuple[float, float]
```

Both functions return **identical raw values** - use `DMAS_ET` for debugging (verbose output) and `DMAS_ET_silent` for production bidding.

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

**⚠️ DEPRECATED**: Cost calculation removed from DMAS-ET (now in bidding layer)

~~Formula: `J = K_ENERGY * total_energy_kJ + K_TARDINESS * total_tardiness_sec`~~

**New Approach (v2.0):**
1. **DMAS-ET** returns raw values: `(E, TFT)`
2. **Auctioneer** calculates baseline: `(E_baseline, TFT_baseline)` for each task
3. **Bidding Service** applies normalization and calculates final bid:
   ```python
   E_norm = E_marginal / E_baseline
   TFT_norm = TFT_marginal / TFT_baseline
   
   b_ms = K_ENERGY * E_norm + K_TIME * TFT_norm  # MiniSum
   b_mm = K_ENERGY * E_norm_total + K_TIME * TFT_norm_total  # MiniMax
   
   b_final = EPSILON * b_ms + (1 - EPSILON) * b_mm  # Hybrid
   ```

**Constants:**
- `K_ENERGY = 0.5` (weight for energy component)
- `K_TIME = 0.5` (weight for time component, **renamed from K_TARDINESS**)
- `EPSILON = 0.5` (hybrid objective weight: MiniSum vs MiniMax)

See [Dynamic Normalization Documentation](../tft-dynamic-normalization.md) for complete algorithm.

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

# Run Exploring Ant (v2.0 - returns tuple)
start_time = datetime.now(timezone.utc)
energy, tft = DMAS_ET(route_plan, start_time, agv_id="AGV_1")

if energy == float('inf') or tft == float('inf'):
    print("Route is invalid or API failed")
else:
    print(f"Total Energy: {energy:.2f} kJ")
    print(f"Total Flow Time: {tft:.2f} seconds")
    print("\nNote: Use bidding_service.py to calculate normalized bid")
```

**Complete Bidding Example:**
```python
from agv_services.auctioneer_service import calculate_baseline_simple
from agv_services.bidding_service import calculate_bid_simple

# 1. Auctioneer calculates baseline for task
E_baseline, TFT_baseline = calculate_baseline_simple(
    distance_to_pickup_m=100.0,
    distance_pickup_to_delivery_m=150.0,
    time_to_pickup_sec=60.0,
    time_pickup_to_delivery_sec=90.0,
    load_kg=200.0
)

# 2. AGV calculates bid using DMAS-ET + normalization
bid = calculate_bid_simple(
    current_route=[],  # AGV's current schedule
    new_task_route=route_plan,  # Route for new task
    global_start_time=start_time,
    E_baseline=E_baseline,
    TFT_baseline=TFT_baseline,
    agv_id="AGV_1"
)

print(f"Normalized bid: {bid:.4f}")
```

## Testing

Run the test suite:
```bash
cd tests
python test_agv_agent.py
```

**Test Coverage:**
1. ✅ Energy calculation functions
2. ✅ Simple route (no conflicts, with TFT tracking)
3. ✅ Route with multiple task endpoints (TFT updates)
4. ✅ Route with varying loads (pickup/dropoff)
5. ✅ Invalid routes (empty, invalid resource)

**Expected Output (v2.0):**
```
Expected Values:
  Energy: 56.250000 kJ
  TFT: 135.00 seconds

Actual Values:
  Energy: 56.250000 kJ
  TFT: 135.00 seconds

[PASS] - Route completed successfully
```

## Silent Mode

For performance testing or batch processing, use `DMAS_ET_silent()` which has identical logic but no console output:

```python
from agv_data.agv_agent import DMAS_ET_silent

energy, tft = DMAS_ET_silent(route_plan, start_time, agv_id="AGV_1")
```

**Note**: Both `DMAS_ET` and `DMAS_ET_silent` return the same `(energy, tft)` tuple. Use the silent version in production bidding to reduce log volume.

## Next Steps

1. **Intention Ant**: When Exploring Ant returns acceptable cost, Intention Ant books the exact slots
2. **Sequential Single Item**: Implement auction mechanism for order selection
3. **Multi-Agent Coordination**: Handle conflicts when multiple AGVs explore same resources

## Configuration

All constants are defined in `agv_data/agv_agent_constants.py`:
- **Energy/Time weights**: `K_ENERGY = 0.5`, `K_TIME = 0.5` (renamed from K_TARDINESS)
- **Hybrid objective**: `EPSILON = 0.5` (MiniSum vs MiniMax balance)
- **Energy parameters**: `C_BASE`, `C_LOAD_COEFF`, `P_IDLE`
- **Normalization fallbacks**: `FALLBACK_NORM_ENERGY_KJ`, `FALLBACK_NORM_TFT_SEC`
- **API configuration**: `RESERVATION_API_URL`

To modify constants, edit `agv_agent_constants.py` and restart the application.

## Total Flow Time (TFT) vs Sum of Tardiness (SOT)

**Key Change in v2.0**: Metric switched from SOT to TFT

| Aspect | SOT (Old) | TFT (New) |
|--------|-----------|-----------|
| **Definition** | Sum of delays beyond deadlines | Time from start to last task completion |
| **Formula** | Σ max(0, t_i - d_i) | t_last - t_start |
| **Works without deadlines?** | ❌ No (returns 0) | ✅ Yes (always positive) |
| **Use case** | Deadline-driven tasks | Minimizing completion time |

**TFT Tracking**: TFT is updated whenever a step has `is_task_endpoint=True`:
```python
if step.is_task_endpoint:
    flow_time_sec = (finish_time - global_start_time).total_seconds()
    total_tft_sec = flow_time_sec  # Updates to latest task completion
```

For routes without task endpoints, TFT = 0 (expected behavior).

## Error Handling

DMAS_ET returns `(float('inf'), float('inf'))` in these cases:
- Route plan is empty
- Any API call fails (network error, server error)
- Invalid API response (missing fields)
- Resource not found (404)

This allows the calling code to reject the route and try alternatives.

**Example:**
```python
energy, tft = DMAS_ET(route_plan, start_time)

if energy == float('inf') or tft == float('inf'):
    print("Route rejected - trying alternative path")
else:
    # Proceed with bidding
    bid = calculate_bid_simple(...)
```

## Performance Considerations

- Each RouteStep makes one API call
- API calls are synchronous (sequential)
- For 10-step route: ~1-2 seconds total (depends on server response time)
- Consider parallel exploration for multiple route alternatives

## Verbose Output Example

```
[DMAS-ET] TEST_AGV_1 starting exploration at 2025-11-08 10:56:23+00:00
[DMAS-ET] Route has 3 steps

--- Step 1/3 ---
Resource ID: 1
Distance: 50.0m, Duration: 30.0s
Load: 100.0kg, Task endpoint: False
Desired start: 2025-11-08 10:56:23+00:00
Earliest available: 2025-11-08 10:56:23+00:00
No delay
Travel energy: 12.500000 kJ
Finish time: 2025-11-08 10:56:53+00:00

--- Step 3/3 ---
Resource ID: 3
...
[TASK ENDPOINT] Flow time: 135.00s

============================================================
[DMAS-ET] TEST_AGV_1 Exploration Complete
============================================================
Total Energy: 56.250000 kJ
Total Flow Time (TFT): 135.00 seconds

⚠️  NOTE: Raw costs returned (E, TFT)
    Normalization & J calculation done by bidding layer
============================================================
```

**Note**: Output now shows **TFT** instead of tardiness, and reminds that normalization happens in bidding layer.

## Related Documentation
- [TFT + Dynamic Normalization](../tft-dynamic-normalization.md) - **NEW in v2.0**
- [Quick Start Guide](./agv-agent-quickstart.md)
- [Implementation Summary](./agv-agent-implementation-summary.md)

## Architecture Changes (v2.0)

```
┌─────────────────────────────────────────┐
│      DMAS_ET / DMAS_ET_silent          │
│  Role: Exploring Ant                    │
│  - Explore route                        │
│  - Query Reservation Table              │
│  - Calculate raw costs: (E, TFT)       │
│  - NO normalization                     │
│  - NO J calculation                     │
└──────────────┬──────────────────────────┘
               │ Returns (E, TFT)
               ▼
┌─────────────────────────────────────────┐
│      Auctioneer Service                 │
│  - Calculate baseline costs             │
│  - (E_baseline, TFT_baseline)          │
│  - Broadcast to AGVs                    │
└──────────────┬──────────────────────────┘
               │ Baseline + Task Info
               ▼
┌─────────────────────────────────────────┐
│      Bidding Service                    │
│  - Call DMAS_ET_silent for J1, J2      │
│  - Apply dynamic normalization          │
│  - Calculate MiniSum + MiniMax bids    │
│  - Return final bid (EPSILON hybrid)   │
└─────────────────────────────────────────┘
```

## See also
- [Reservation Table](/docs/reservation-table/reservation-table.md)
- [Journey Phase Implementation](../journey-phase-implementation.md)
- [WebSocket Protocol](../websocket-protocol-explanation.md)