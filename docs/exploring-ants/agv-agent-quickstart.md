# AGV Agent (Exploring Ant) - Quick Start Guide

## What is Exploring Ant?

**Exploring Ant** is a virtual AGV that simulates a journey through a route plan to calculate the total cost (energy + tardiness). It's part of the D-MAS (Delegate Multi-Agent System) architecture.

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

### 3. Run Exploring Ant

```python
start_time = datetime.now(timezone.utc)
cost = DMAS_ET(route_plan, start_time, agv_id="AGV_1")

if cost == float('inf'):
    print("Route failed!")
else:
    print(f"Cost: {cost}")
```

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

# Run simulation
start_time = datetime.now(timezone.utc)
cost = DMAS_ET(route_plan, start_time, agv_id="AGV_1")

print(f"Total Cost: {cost}")
```

## Understanding the Output

```
[DMAS-ET] AGV_1 starting exploration at 2025-11-08 06:30:00+00:00
[DMAS-ET] Route has 4 steps

--- Step 1/4 ---
Resource ID: 1
Distance: 100.0m, Duration: 60.0s
Load: 0.0kg, Task endpoint: False
Desired start: 2025-11-08 06:30:00+00:00
Earliest available: 2025-11-08 06:30:00+00:00  ← No conflict
No delay
Travel energy: 5.000000 kJ
Finish time: 2025-11-08 06:31:00+00:00

--- Step 2/4 ---
Resource ID: 2
...
✓ On time (due: 2025-11-08 06:35:00+00:00)  ← Task completed before deadline

============================================================
[DMAS-ET] AGV_1 Exploration Complete
============================================================
Total Energy: 77.500000 kJ
Total Tardiness: 0.00 seconds
Cost J = 0.5 * 77.500000 + 0.5 * 0.00
Cost J = 38.750000
============================================================
```

## When to Use

✅ **Use Exploring Ant when:**
- You want to evaluate if a route is feasible
- You need to compare multiple route alternatives
- You want to predict delays and tardiness
- You're implementing AGV bidding/auction systems

❌ **Don't use Exploring Ant for:**
- Actually booking resources (use Intention Ant / book_slot API)
- Real-time AGV control (this is simulation only)

## Cost Interpretation

**Cost J = Energy Cost + Tardiness Cost**

- Lower cost = better route
- `inf` = route is impossible or API failed
- Energy increases with distance and load
- Tardiness increases when missing deadlines

**Example Comparison:**
```
Route A: Cost = 28.5 (low energy, no tardiness)  ← Better choice
Route B: Cost = 45.0 (high energy, some tardiness)
Route C: Cost = inf  (resource unavailable)      ← Impossible
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

**Issue:** Route returns `inf`
- Check that all resource IDs exist in database
- Verify timestamps are in the future
- Check server logs for errors

**Issue:** High tardiness cost
- Route may be too long for the deadlines
- Resources may be heavily booked (delays)
- Try alternative routes or later start times

## Next Steps

1. ✅ Test with simple routes (see `test_agv_agent.py`)
2. ⏳ Implement Intention Ant to actually book resources
3. ⏳ Implement Sequential Single Item auction mechanism
4. ⏳ Integrate with existing AGV pathfinding system

## Constants Reference

All defined in `agv_agent_constants.py`:

```python
K_ENERGY = 0.5          # Energy weight in cost
K_TARDINESS = 0.5       # Tardiness weight in cost
C_BASE = 0.05           # Base energy (kJ/m)
C_LOAD_COEFF = 0.002    # Load energy (kJ/(kg·m))
P_IDLE = 0.1            # Idle power (W)
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
