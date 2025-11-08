# AGV Agent (Exploring Ant) - Quick Start Guide

## What is Exploring Ant?

**Exploring Ant** is a virtual AGV that simulates a journey through a route plan to calculate **raw costs** (energy and Total Flow Time). It's part of the D-MAS (Delegate Multi-Agent System) architecture.

**⚠️ v2.0 Update**: Exploring Ant now returns `(energy, TFT)` tuple instead of weighted cost J. Normalization and bidding logic moved to separate service layer.

## What's New in v2.0?

| Change | Before (v1.x) | After (v2.0) |
|--------|---------------|--------------|
| **Metric** | SOT (Sum of Tardiness) | **TFT (Total Flow Time)** |
| **Return Type** | `float` (cost J) | **`Tuple[float, float]`** (E, TFT) |
| **Normalization** | None | **Dynamic Baseline** (in bidding layer) |
| **Constant** | K_TARDINESS | **K_TIME** |

See [TFT Documentation](../tft-dynamic-normalization.md) for details.

## Installation

No installation needed! All dependencies are already installed.

## Basic Usage

### 1. Import Required Classes

```python
from datetime import datetime, timedelta, timezone
from agv_data.agv_agent import RouteStep, DMAS_ET
```

### 2. Create a Route Plan

```python
route_plan = [
    RouteStep(
        resource_id=1,        # Which resource (CA/LSA) to use
        distance_m=50.0,      # Distance in meters
        duration_sec=30.0,    # Time to complete step
        load_kg=100.0,        # Load weight in kg
        is_task_endpoint=False, # Is this a pickup/dropoff point?
        due_date=None         # Deadline (if task endpoint)
    ),
    # Add more steps...
]
```

### 3. Run Exploring Ant (v2.0)

```python
start_time = datetime.now(timezone.utc)
energy, tft = DMAS_ET(route_plan, start_time, agv_id="AGV_1")

if energy == float('inf') or tft == float('inf'):
    print("Route failed!")
else:
    print(f"Energy: {energy:.2f} kJ")
    print(f"Total Flow Time: {tft:.2f} seconds")
```

**Note**: Return type changed from single `cost` to tuple `(energy, tft)`.

## Full Example

```python
from datetime import datetime, timedelta, timezone
from agv_data.agv_agent import RouteStep, DMAS_ET

# Scenario: AGV picks up item from warehouse and delivers to station
route_plan = [
    # Step 1: Empty AGV travels to warehouse
    RouteStep(
        resource_id=1,
        distance_m=100.0,
        duration_sec=60.0,
        load_kg=0.0,  # Empty
        is_task_endpoint=False
    ),
    
    # Step 2: Pick up item (200kg)
    RouteStep(
        resource_id=2,
        distance_m=10.0,
        duration_sec=30.0,
        load_kg=200.0,  # Loaded
        is_task_endpoint=True,
        due_date=datetime.now(timezone.utc) + timedelta(minutes=5)
    ),
    
    # Step 3: Travel to destination
    RouteStep(
        resource_id=3,
        distance_m=150.0,
        duration_sec=90.0,
        load_kg=200.0,  # Still loaded
        is_task_endpoint=False
    ),
    
    # Step 4: Drop off item
    RouteStep(
        resource_id=4,
        distance_m=10.0,
        duration_sec=30.0,
        load_kg=0.0,  # Empty again
        is_task_endpoint=True,
        due_date=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
]

# Run simulation (v2.0 - returns tuple)
start_time = datetime.now(timezone.utc)
energy, tft = DMAS_ET(route_plan, start_time, agv_id="AGV_1")

print(f"Total Energy: {energy:.2f} kJ")
print(f"Total Flow Time: {tft:.2f} seconds")

# For bidding, use bidding_service to calculate normalized bid
from agv_services.bidding_service import calculate_bid_simple
from agv_services.auctioneer_service import calculate_baseline_simple

# Auctioneer calculates baseline
E_baseline, TFT_baseline = calculate_baseline_simple(
    distance_to_pickup_m=100.0,
    distance_pickup_to_delivery_m=160.0,
    time_to_pickup_sec=60.0,
    time_pickup_to_delivery_sec=120.0,
    load_kg=200.0
)

# AGV calculates bid
bid = calculate_bid_simple(
    current_route=[],
    new_task_route=route_plan,
    global_start_time=start_time,
    E_baseline=E_baseline,
    TFT_baseline=TFT_baseline,
    agv_id="AGV_1"
)

print(f"Normalized Bid: {bid:.4f}")
```

## Understanding the Output

```
[DMAS-ET] AGV_1 starting exploration at 2025-11-08 10:56:23+00:00
[DMAS-ET] Route has 4 steps

--- Step 1/4 ---
Resource ID: 1
Distance: 100.0m, Duration: 60.0s
Load: 0.0kg, Task endpoint: False
Desired start: 2025-11-08 10:56:23+00:00
Earliest available: 2025-11-08 10:56:23+00:00  ← No conflict
No delay
Travel energy: 5.000000 kJ
Finish time: 2025-11-08 10:57:23+00:00

--- Step 2/4 ---
Resource ID: 2
...
[TASK ENDPOINT] Flow time: 90.00s  ← TFT for first task
✓ On time (due: 2025-11-08 11:01:23+00:00)

--- Step 4/4 ---
...
[TASK ENDPOINT] Flow time: 240.00s  ← TFT updated to last task

============================================================
[DMAS-ET] AGV_1 Exploration Complete
============================================================
Total Energy: 77.500000 kJ
Total Flow Time (TFT): 240.00 seconds

⚠️  NOTE: Raw costs returned (E, TFT)
    Normalization & J calculation done by bidding layer
============================================================
```

**Key Changes in v2.0:**
- Shows **TFT** (Total Flow Time) instead of tardiness
- No longer calculates `Cost J` in Exploring Ant
- Raw values `(E, TFT)` returned for bidding layer

## When to Use

✅ **Use Exploring Ant when:**
- You want to get raw costs (energy, TFT) for a route
- You need to evaluate if a route is feasible
- You're implementing AGV bidding/auction systems (with bidding_service)
- You want to predict delays

❌ **Don't use Exploring Ant for:**
- Direct cost comparison (use bidding_service with normalization)
- Actually booking resources (use Intention Ant / book_slot API)
- Real-time AGV control (this is simulation only)

## Cost Interpretation (v2.0)

**Raw Values**: Exploring Ant returns `(E, TFT)` without weighting or normalization

- Lower energy/TFT = more efficient route
- `(inf, inf)` = route is impossible or API failed
- Energy increases with distance and load
- TFT increases with route length and delays

**For Bidding**: Use `bidding_service.calculate_bid_simple()` which applies:
1. Dynamic normalization (divide by baseline)
2. K_ENERGY/K_TIME weighting
3. EPSILON hybrid objective (MiniSum + MiniMax)

**Example Comparison:**
```python
# Route A
energy_A, tft_A = DMAS_ET(route_A, start_time)
# → (56.25 kJ, 135.0 sec)

# Route B
energy_B, tft_B = DMAS_ET(route_B, start_time)
# → (80.0 kJ, 200.0 sec)

# Can't compare directly! Need normalization:
bid_A = calculate_bid_simple(..., E_baseline, TFT_baseline, ...)
bid_B = calculate_bid_simple(..., E_baseline, TFT_baseline, ...)
# → Now bids are comparable across different tasks
```

## Testing Your Routes

```bash
cd tests
python test_agv_agent.py
```

This runs 5 test scenarios to verify everything works correctly.

## Common Issues

**Issue:** API call fails (400 Bad Request)
- ✅ Make sure Django server is running: `docker compose up`
- ✅ Check that sample resources exist: `python create_sample_resources.py`

**Issue:** Route returns `(inf, inf)`
- Check that all resource IDs exist in database
- Verify timestamps are in the future
- Check server logs for errors

**Issue:** High TFT value
- Route may be too long
- Resources may be heavily booked (delays)
- Try alternative routes or later start times

**Issue:** TypeError: cannot unpack non-iterable float
- You may be using old code (v1.x) that expects single return value
- Update to: `energy, tft = DMAS_ET(...)` instead of `cost = DMAS_ET(...)`

## Next Steps

1. ✅ Test with simple routes (see `test_agv_agent.py`)
2. ✅ Understand TFT vs SOT (see [TFT Documentation](../tft-dynamic-normalization.md))
3. ✅ Use bidding_service for normalized bid calculation
4. ⏳ Implement Intention Ant to actually book resources
5. ⏳ Implement Sequential Single Item auction mechanism
6. ⏳ Integrate with existing AGV pathfinding system

## Constants Reference

All defined in `agv_agent_constants.py`:

```python
# v2.0 Constants
K_ENERGY = 0.5          # Energy weight in bid calculation
K_TIME = 0.5            # Time weight (renamed from K_TARDINESS)
EPSILON = 0.5           # Hybrid objective (MiniSum vs MiniMax)

# Energy parameters
C_BASE = 0.05           # Base energy (kJ/m)
C_LOAD_COEFF = 0.002    # Load energy (kJ/(kg·m))
P_IDLE = 0.1            # Idle power (W)

# Normalization fallbacks
FALLBACK_NORM_ENERGY_KJ = 1.0
FALLBACK_NORM_TFT_SEC = 1.0
```

## API Endpoint Used

```
POST /api/agvs/reservation/resource/{resource_id}/query_slot/

Request:
{
    "request_start_time": "2025-11-08T06:30:00Z",
    "duration_seconds": 30
}

Response:
{
    "resource_id": 1,
    "earliest_available_start": "2025-11-08T06:30:00Z",
    "calculated_delay_seconds": 0.0
}
```

## Full Documentation

See [agv-agent-exploring-ant.md](./agv-agent-exploring-ant.md) for comprehensive documentation.
