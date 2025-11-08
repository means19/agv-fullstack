# TFT (Total Flow Time) + Dynamic Baseline Normalization

## Overview

This document describes the implementation of **Total Flow Time (TFT)** metric and **Dynamic Baseline Normalization** for the SSI-DMAS-ET (Sequential Single-Item Auction with Distributed Multi-Agent Search and Energy-Time optimization) algorithm.

### Key Changes from Previous Implementation

1. **Metric Change**: Sum of Tardiness (SOT) → Total Flow Time (TFT)
2. **Normalization**: Static normalization → Dynamic Baseline Normalization
3. **Hybrid Objective**: Added EPSILON parameter to balance MiniSum and MiniMax strategies

---

## 1. Total Flow Time (TFT)

### Definition

**TFT** is the time elapsed from the global schedule start time to the completion of the last task endpoint.

```
TFT = t_completion_last_task - t_schedule_start
```

### Why TFT Instead of SOT?

| Metric | Formula | Advantages | Disadvantages |
|--------|---------|------------|---------------|
| **SOT** (Sum of Tardiness) | Σ max(0, t_i - d_i) | Clear penalty signal for late tasks | Only works when deadlines exist; Returns 0 when all tasks are early |
| **TFT** (Total Flow Time) | t_last - t_start | Always positive; Works without deadlines; Measures schedule efficiency | Less intuitive for deadline-driven tasks |

**Use Case**:
- SOT: When tasks have strict deadlines and tardiness penalties matter
- TFT: When minimizing total completion time is the goal (no deadlines, or deadlines are very loose)

### Implementation

In `agv_agent.py`, TFT is tracked during DMAS-ET exploration:

```python
def DMAS_ET(route_plan: List[RouteStep], global_start_time: datetime, agv_id: str = "AGV") -> Tuple[float, float]:
    """
    Returns RAW costs (E, TFT) without normalization.
    Normalization is handled by the bidding layer.
    """
    total_energy_kj = 0.0
    total_tft_sec = 0.0  # Total Flow Time
    current_time = global_start_time
    
    for step in route_plan:
        # ... (reservation and energy calculation)
        
        if step.is_task_endpoint:
            # Calculate flow time for this task
            flow_time_sec = (finish_time - global_start_time).total_seconds()
            total_tft_sec = flow_time_sec  # Update to latest task completion
            
            print(f"[TASK ENDPOINT] Flow time: {flow_time_sec:.2f}s")
    
    # Return RAW costs (NO J calculation here)
    # Normalization & K_ENERGY/K_TIME weighting done by bidding layer
    return (total_energy_kj, total_tft_sec)
```

**Silent Version** (for bidding):
```python
def DMAS_ET_silent(route_plan: List[RouteStep], global_start_time: datetime, agv_id: str = "AGV") -> Tuple[float, float]:
    # ... (same logic without printing)
    return (total_energy_kj, total_tft_sec)
```

**⚠️ Important**: Both functions return **raw values** `(E, TFT)` as a tuple, NOT the weighted cost `J`. This allows the bidding layer to apply dynamic normalization before calculating the final bid.

---

## 2. Dynamic Baseline Normalization

### Problem

Different tasks have different scales:
- **Task A**: Short distance, light load → Small energy/time costs
- **Task B**: Long distance, heavy load → Large energy/time costs

Without normalization, AGV bids are **not comparable** across different tasks.

### Solution: Dynamic Baseline Normalization

For each task, calculate the **ideal baseline costs** (what an unloaded AGV traveling the shortest path would cost):

```
E_baseline = (C_BASE + 0) * d_pickup + (C_BASE + C_LOAD_COEFF * load) * d_delivery
TFT_baseline = t_pickup + t_delivery
```

Then normalize actual costs:

```
E_normalized = E_marginal / E_baseline
TFT_normalized = TFT_marginal / TFT_baseline
```

### Implementation: `auctioneer_service.py`

```python
def calculate_baseline_simple(
    distance_to_pickup_m: float,
    distance_pickup_to_delivery_m: float,
    time_to_pickup_sec: float,
    time_pickup_to_delivery_sec: float,
    load_kg: float
) -> Tuple[float, float]:
    """
    Calculate baseline costs for a task using ideal Dijkstra path.
    
    Returns:
        (E_baseline_kj, TFT_baseline_sec)
    """
    from agv_data.agv_agent_constants import (
        C_BASE, C_LOAD_COEFF, 
        FALLBACK_NORM_ENERGY_KJ, FALLBACK_NORM_TFT_SEC
    )
    
    # Segment 1: Empty travel to pickup
    E_seg1 = (C_BASE + 0) * distance_to_pickup_m
    
    # Segment 2: Loaded travel from pickup to delivery
    E_seg2 = (C_BASE + C_LOAD_COEFF * load_kg) * distance_pickup_to_delivery_m
    
    # Total baseline energy (in kJ)
    E_baseline_kj = E_seg1 + E_seg2
    
    # Total baseline time (in seconds)
    TFT_baseline_sec = time_to_pickup_sec + time_pickup_to_delivery_sec
    
    # Apply fallback if baseline is zero
    if E_baseline_kj == 0:
        E_baseline_kj = FALLBACK_NORM_ENERGY_KJ
    if TFT_baseline_sec == 0:
        TFT_baseline_sec = FALLBACK_NORM_TFT_SEC
    
    return (E_baseline_kj, TFT_baseline_sec)
```

### Example Calculation

**Task**: Pickup at 100m away, deliver 150m further, load = 200kg, times = 60s + 90s

```python
# Constants
C_BASE = 0.05 kJ/m
C_LOAD_COEFF = 0.002 kJ/(kg·m)

# Segment 1 (empty to pickup)
E_seg1 = (0.05 + 0) * 100 = 5.0 kJ

# Segment 2 (loaded to delivery)
E_seg2 = (0.05 + 0.002 * 200) * 150 = (0.05 + 0.4) * 150 = 67.5 kJ

# Total baseline
E_baseline = 5.0 + 67.5 = 72.5 kJ
TFT_baseline = 60 + 90 = 150 seconds
```

---

## 3. Bid Calculation with Hybrid Objective

### Algorithm: BID_CALCULATION_ET

The bidding process combines **MiniSum** (marginal cost) and **MiniMax** (total cost) strategies:

```
b_final = EPSILON * b_ms + (1 - EPSILON) * b_mm
```

Where:
- **b_ms** (MiniSum bid): Focuses on marginal cost increase
- **b_mm** (MiniMax bid): Focuses on total cost after accepting task
- **EPSILON**: Weight parameter (0.5 = equal balance)

### Implementation: `bidding_service.py`

```python
def calculate_bid_simple(
    current_route: List[RouteStep],
    new_task_route: List[RouteStep],
    global_start_time: datetime,
    E_baseline: float,
    TFT_baseline: float,
    agv_id: str = "AGV"
) -> float:
    """
    Calculate AGV bid for a new task using dynamic normalization.
    
    Steps:
    1. Get J1 (current schedule costs)
    2. Run DMAS_ET for J2 (costs with new task)
    3. Calculate marginal costs
    4. Normalize by baseline
    5. Calculate MiniSum bid (marginal)
    6. Calculate MiniMax bid (total)
    7. Combine using EPSILON
    
    Returns:
        b_final (normalized bid)
    """
    from agv_data.agv_agent import DMAS_ET_silent
    from agv_data.agv_agent_constants import (
        K_ENERGY, K_TIME, EPSILON,
        FALLBACK_NORM_ENERGY_KJ, FALLBACK_NORM_TFT_SEC
    )
    
    # Step 1: Get current costs (J1)
    if current_route:
        E_j1, TFT_j1 = DMAS_ET_silent(current_route, global_start_time, agv_id)
    else:
        E_j1, TFT_j1 = 0.0, 0.0
    
    # Step 2: Get costs with new task (J2)
    combined_route = current_route + new_task_route
    E_j2, TFT_j2 = DMAS_ET_silent(combined_route, global_start_time, agv_id)
    
    # Step 3: Calculate marginal costs
    E_marginal = E_j2 - E_j1
    TFT_marginal = TFT_j2 - TFT_j1
    
    # Step 4: Normalize
    E_baseline_safe = E_baseline if E_baseline > 0 else FALLBACK_NORM_ENERGY_KJ
    TFT_baseline_safe = TFT_baseline if TFT_baseline > 0 else FALLBACK_NORM_TFT_SEC
    
    E_norm_marginal = E_marginal / E_baseline_safe
    TFT_norm_marginal = TFT_marginal / TFT_baseline_safe
    
    E_norm_total = E_j2 / E_baseline_safe
    TFT_norm_total = TFT_j2 / TFT_baseline_safe
    
    # Step 5: MiniSum bid (marginal)
    b_ms = K_ENERGY * E_norm_marginal + K_TIME * TFT_norm_marginal
    
    # Step 6: MiniMax bid (total)
    b_mm = K_ENERGY * E_norm_total + K_TIME * TFT_norm_total
    
    # Step 7: Hybrid objective
    b_final = EPSILON * b_ms + (1 - EPSILON) * b_mm
    
    return b_final
```

### Example Bid Calculation

**Scenario**:
- Current route: Empty (E_j1 = 0, TFT_j1 = 0)
- New task: E_baseline = 72.5 kJ, TFT_baseline = 150s
- After DMAS-ET: E_j2 = 80 kJ, TFT_j2 = 180s

```python
# Constants
K_ENERGY = 0.5
K_TIME = 0.5
EPSILON = 0.5

# Marginal costs
E_marginal = 80 - 0 = 80 kJ
TFT_marginal = 180 - 0 = 180s

# Normalization
E_norm_marginal = 80 / 72.5 = 1.103
TFT_norm_marginal = 180 / 150 = 1.200

E_norm_total = 80 / 72.5 = 1.103
TFT_norm_total = 180 / 150 = 1.200

# Bids
b_ms = 0.5 * 1.103 + 0.5 * 1.200 = 1.152
b_mm = 0.5 * 1.103 + 0.5 * 1.200 = 1.152

# Final bid
b_final = 0.5 * 1.152 + 0.5 * 1.152 = 1.152
```

---

## 4. Constants Configuration

### `agv_agent_constants.py`

```python
# Objective function weights
K_ENERGY = 0.5  # Weight for energy cost
K_TIME = 0.5    # Weight for time cost (TFT)

# Hybrid objective parameter
EPSILON = 0.5   # Balance between MiniSum (0) and MiniMax (1)

# Energy parameters
C_BASE = 0.05           # Base energy consumption (kJ/m)
C_LOAD_COEFF = 0.002    # Load coefficient (kJ/(kg·m))
P_IDLE = 0.1            # Idle power (W)

# Normalization fallback values
FALLBACK_NORM_ENERGY_KJ = 1.0   # Used when E_baseline = 0
FALLBACK_NORM_TFT_SEC = 1.0     # Used when TFT_baseline = 0
```

### Parameter Tuning Guide

| Parameter | Range | Effect |
|-----------|-------|--------|
| **K_ENERGY** | [0, 1] | Higher = prioritize energy efficiency |
| **K_TIME** | [0, 1] | Higher = prioritize faster completion |
| **EPSILON** | [0, 1] | 0 = Pure MiniSum, 1 = Pure MiniMax, 0.5 = Balanced |
| **C_BASE** | > 0 | Higher = more energy cost per meter |
| **C_LOAD_COEFF** | > 0 | Higher = more energy cost for heavy loads |

**Constraint**: K_ENERGY + K_TIME should equal 1.0 for balanced optimization

---

## 5. Integration Example

### Full Auction Flow

```python
from agv_services.auctioneer_service import calculate_baseline_simple
from agv_services.bidding_service import calculate_bid_simple
from datetime import datetime, timezone

# 1. Auctioneer calculates baseline for new task
E_baseline, TFT_baseline = calculate_baseline_simple(
    distance_to_pickup_m=100.0,
    distance_pickup_to_delivery_m=150.0,
    time_to_pickup_sec=60.0,
    time_pickup_to_delivery_sec=90.0,
    load_kg=200.0
)
# Result: E_baseline=72.5 kJ, TFT_baseline=150s

# 2. Broadcast task with baseline to all AGVs
task_announcement = {
    "task_id": "T001",
    "pickup_location": "W1",
    "delivery_location": "W2",
    "load_kg": 200.0,
    "E_baseline": E_baseline,
    "TFT_baseline": TFT_baseline
}

# 3. Each AGV calculates bid
bids = {}
for agv in agv_fleet:
    bid = calculate_bid_simple(
        current_route=agv.current_schedule,
        new_task_route=agv.plan_route_for_task(task_announcement),
        global_start_time=datetime.now(timezone.utc),
        E_baseline=E_baseline,
        TFT_baseline=TFT_baseline,
        agv_id=agv.id
    )
    bids[agv.id] = bid

# 4. Auctioneer selects winner (lowest bid)
winner_id = min(bids, key=bids.get)
print(f"Task {task_announcement['task_id']} assigned to {winner_id}")
print(f"Winning bid: {bids[winner_id]:.4f}")
```

---

## 6. Testing

### Test Suite: `tests/test_agv_agent.py`

Key test cases:

1. **Energy Calculation**: Verify travel and wait energy formulas
2. **Simple Route with TFT**: Route with task endpoints → TFT > 0
3. **Multiple Task Endpoints**: TFT updates to latest task completion
4. **Varying Loads**: Different loads affect energy correctly
5. **Invalid Routes**: Empty routes and invalid resources return `inf`

**Run tests**:
```bash
python tests/test_agv_agent.py
```

**Expected output**:
```
============================================================
TEST 2: Simple Route (No Conflicts)
============================================================
Total Energy: 56.250000 kJ
Total Flow Time (TFT): 135.00 seconds
Cost J = 95.625000
[PASS] - Route completed successfully
```

### Test Suite: `tests/test_auctioneer_service.py`

Tests baseline calculation:

```python
def test_baseline_calculation():
    E_baseline, TFT_baseline = calculate_baseline_simple(
        distance_to_pickup_m=100.0,
        distance_pickup_to_delivery_m=150.0,
        time_to_pickup_sec=60.0,
        time_pickup_to_delivery_sec=90.0,
        load_kg=200.0
    )
    
    assert E_baseline == 72.5, f"Expected 72.5, got {E_baseline}"
    assert TFT_baseline == 150.0, f"Expected 150.0, got {TFT_baseline}"
    print("[PASS] Baseline calculation correct")
```

---

## 7. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Auctioneer                        │
│  - Receives new task                                │
│  - Calculates baseline (E_baseline, TFT_baseline)   │
│  - Broadcasts task + baseline to AGVs               │
│  - Selects winner (lowest bid)                      │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │  Task Announcement  │
        │  + Baseline Costs   │
        └──────────┬──────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐     ┌───────────────┐
│    AGV 1      │     │    AGV 2      │
│  - Run DMAS-ET│     │  - Run DMAS-ET│
│  - Normalize  │     │  - Normalize  │
│  - Submit bid │     │  - Submit bid │
└───────────────┘     └───────────────┘
```

### File Structure

```
agv_server/
├── agv_data/
│   ├── agv_agent_constants.py      # Constants (K_ENERGY, K_TIME, EPSILON)
│   ├── agv_agent.py                # DMAS-ET exploration (returns E, TFT)
│   └── ...
├── agv_services/
│   ├── auctioneer_service.py       # Baseline calculation
│   └── bidding_service.py          # Bid calculation with normalization
└── ...

tests/
├── test_agv_agent.py               # DMAS-ET tests
└── test_auctioneer_service.py      # Baseline calculation tests
```

---

## 8. Performance Considerations

### When to Use TFT vs SOT

| Scenario | Recommended Metric | Reason |
|----------|-------------------|--------|
| Tasks with strict deadlines | **SOT** | Directly penalizes tardiness |
| Tasks without deadlines | **TFT** | Always provides optimization signal |
| Mixed (some tasks have deadlines) | **TFT** | More robust, works for all cases |
| Real-time responsiveness critical | **TFT** | Minimizes overall completion time |

### Computational Complexity

- **DMAS-ET**: O(n) where n = number of steps in route
- **Baseline Calculation**: O(1) - simple arithmetic
- **Bid Calculation**: O(n) - dominated by DMAS-ET call
- **Auction**: O(m * n) where m = number of AGVs, n = avg route length

### Optimization Tips

1. **Cache baseline calculations**: Same task type → same baseline
2. **Parallel bidding**: AGVs can bid in parallel
3. **Early termination**: Stop DMAS-ET if cost exceeds threshold
4. **Route pruning**: Remove infeasible routes before DMAS-ET

---

## 9. Future Enhancements

### Potential Improvements

1. **Adaptive EPSILON**: Adjust based on system load
   ```python
   # High load → prioritize total cost (MiniMax)
   EPSILON = 0.2 if system_load > 0.8 else 0.5
   ```

2. **Multi-task baselines**: Calculate baseline for task bundles
3. **Historical learning**: Adjust K_ENERGY/K_TIME based on past performance
4. **Deadline awareness**: Hybrid TFT + SOT when some tasks have deadlines

### Research Directions

- Impact of EPSILON on system makespan and energy consumption
- Comparison with static normalization methods
- Performance in high-conflict scenarios (dense reservation table)
- Fairness guarantees across heterogeneous AGV fleets

---

## 10. References

### Related Documentation

- `journey-phase-implementation.md`: Journey phase state machine
- `websocket-protocol-explanation.md`: Real-time communication protocol
- `reservation_table.md`: Resource reservation system
- `data-frame-CRC.md`: AGV-Server communication format

### Key Algorithms

- **SSI-DMAS-ET**: Sequential Single-Item Auction with Distributed Multi-Agent Search
- **EPSILON Hybrid**: Balanced MiniSum-MiniMax objective
- **Dynamic Normalization**: Task-specific baseline scaling

---

## Appendix: Quick Reference

### Constants
```python
K_ENERGY = 0.5
K_TIME = 0.5
EPSILON = 0.5
C_BASE = 0.05 kJ/m
C_LOAD_COEFF = 0.002 kJ/(kg·m)
```

### Formulas

**TFT**:
```
TFT = t_completion_last_task - t_schedule_start
```

**Baseline**:
```
E_baseline = C_BASE * d1 + (C_BASE + C_LOAD_COEFF * load) * d2
TFT_baseline = t1 + t2
```

**Bid**:
```
b_ms = K_ENERGY * (E_marginal / E_baseline) + K_TIME * (TFT_marginal / TFT_baseline)
b_mm = K_ENERGY * (E_total / E_baseline) + K_TIME * (TFT_total / TFT_baseline)
b_final = EPSILON * b_ms + (1 - EPSILON) * b_mm
```

### API Endpoints

```python
# Baseline calculation
from agv_services.auctioneer_service import calculate_baseline_simple
E_baseline, TFT_baseline = calculate_baseline_simple(d1, d2, t1, t2, load)

# Bid calculation
from agv_services.bidding_service import calculate_bid_simple
bid = calculate_bid_simple(current_route, new_task_route, start_time, E_baseline, TFT_baseline, agv_id)

# DMAS-ET exploration
from agv_data.agv_agent import DMAS_ET_silent
E, TFT = DMAS_ET_silent(route_plan, start_time, agv_id)
```

---
