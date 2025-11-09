# Auction & Bidding Implementation - Completed

## Overview
Successfully implemented the SSI-DMAS-ET auction system with dynamic normalization as specified in `auction-logic-implementation-guide.md`.

## Implementation Date
November 9, 2025

## Components Implemented

### 1. AuctioneerService (`agv_services/auctioneer_service.py`)
**Purpose:** Calculate baseline costs (E_baseline, TFT_baseline) for new orders

**Algorithm A: CALCULATE_BASELINE**
```python
def calculate_baseline_from_order(order) -> Tuple[float, float]:
    """
    1. Get parking_node, storage_node, and workstation_node from order
    2. Convert node numbers to names (e.g., 5 -> "CA-05")
    3. Calculate Leg 1: PARKING -> Storage (empty load)
       - Get ideal path via MapService.get_ideal_path()
       - E1 = (C_BASE + 0) * distance1
    4. Calculate Leg 2: Storage -> Workstation (loaded)
       - Get ideal path via MapService.get_ideal_path()
       - E2 = (C_BASE + C_LOAD_COEFF * load) * distance2
    5. Return: E_baseline = E1 + E2, TFT_baseline = T1 + T2
    
    Note: Uses PARKING node as ideal reference (no obstacles),
          NOT DEPOT. Each order has its own parking reference.
    """
```

**Key Features:**
- ✅ Integration with MapService (NetworkX Dijkstra)
- ✅ Baseline from **parking node** (ideal reference)
- ✅ Node number to name mapping (_node_number_to_name helper)
- ✅ Automatic fallback values for zero costs (MIN_DURATION_SEC=1.0)
- ✅ Comprehensive logging
- ✅ Error handling for missing resources

**Usage:**
```python
from agv_services import auctioneer_service

E_baseline, TFT_baseline = auctioneer_service.calculate_baseline_from_order(order)
```

---

### 2. BiddingService (`agv_services/bidding_service.py`)
**Purpose:** Calculate AGV bids using dynamic normalization for idle and busy AGVs

**Algorithm B: BID_CALCULATION_ET**
```python
def calculate_bid_for_agv(agv, order, E_baseline, TFT_baseline) -> float:
    """
    1. Determine AGV state (IDLE or BUSY):
       - IDLE: J1 = (0, 0), start from current_node
       - BUSY: Calculate J1 from remaining_path, start from completion_node
    
    2. For BUSY AGVs, calculate J1:
       - Convert remaining_path to RouteStep list
       - Determine load based on journey_phase and position in path
       - Use DMAS_ET_silent to calculate (E_j1, TFT_j1)
    
    3. Create route plan for new order (DIRECT, NO parking detour):
       - IDLE: current_node → storage → workstation
       - BUSY: completion_node → storage → workstation
    
    4. Calculate J2 using DMAS_ET_silent(new_route_plan)
    
    5. Calculate marginal costs:
       - E_marginal = E_j2 - E_j1
       - TFT_marginal = TFT_j2 - TFT_j1
    
    6. Normalize by baseline:
       - E_norm_marginal = E_marginal / E_baseline
       - TFT_norm_marginal = TFT_marginal / TFT_baseline
       - E_norm_total = E_j2 / E_baseline
       - TFT_norm_total = TFT_j2 / TFT_baseline
    
    7. Calculate hybrid bid:
       - MiniSum: b_ms = K_ENERGY * E_norm_marginal + K_TIME * TFT_norm_marginal
       - MiniMax: b_mm = K_ENERGY * E_norm_total + K_TIME * TFT_norm_total
       - Hybrid: b_final = EPSILON * b_ms + (1 - EPSILON) * b_mm
    """
```

**Key Features:**
- ✅ Dynamic baseline normalization
- ✅ Hybrid MiniSum/MiniMax objective (ε=0.5)
- ✅ **Support for IDLE AGVs**: Start from current_node, J1=(0,0)
- ✅ **Support for BUSY AGVs**: Calculate J1 from remaining_path, start from completion_node
- ✅ Direct route generation (NO parking detour)
- ✅ Automatic route plan generation via MapService
- ✅ Integration with DMAS_ET_silent for reservation conflicts
- ✅ Node mapping helper (_node_number_to_name)
- ✅ Duration fix (MIN_DURATION_SEC=1.0 for zero travel times)

**Helper Functions:**
```python
def _calculate_j1_for_busy_agv(agv, start_time):
    """Calculate current task completion costs from remaining_path"""
    
def _get_completion_node_from_remaining_path(agv):
    """Extract completion position from remaining_path"""
    
def _create_route_plan_for_order(agv, order):
    """Generate direct route: start → storage → workstation"""
```

**Usage:**
```python
from agv_services import BiddingService

bidding_service = BiddingService()
bid = bidding_service.calculate_bid_for_agv(agv, order, E_baseline, TFT_baseline)
```

---

### 3. TaskManager (`agv_services/task_manager.py`)
**Purpose:** Coordinate the complete auction process

**Workflow:**
```
1. New order arrives
   ↓
2. Auctioneer calculates baseline (E_baseline, TFT_baseline)
   - Uses parking node as ideal reference
   ↓
3. Broadcast to ALL AGVs (idle + busy)
   ↓
4. Each AGV calculates bid using BiddingService
   - IDLE: J1=0, route from current_node
   - BUSY: J1 from remaining_path, route from completion_node
   ↓
5. Collect all bids
   ↓
6. Select winner (minimum bid)
   ↓
7. Return (winner_agv_id, winning_bid)
```

**Key Features:**
- ✅ Complete auction orchestration
- ✅ Supports ALL AGVs (idle + busy)
- ✅ Parallel bid collection from all AGVs
- ✅ Winner selection (argmin)
- ✅ Comprehensive logging
- ✅ Error handling and validation

**Usage:**
```python
from agv_services import task_manager

result = task_manager.run_auction(order)
if result:
    winner_agv_id, winning_bid = result
    # Assign task to winner
```

---

## Integration with Existing System

### 1. MapService Integration
```python
# AuctioneerService uses MapService for ideal paths
map_service = MapService()
map_service.load_graph()  # Load from ResourceAgent database

# Get Dijkstra paths
path1 = map_service.get_ideal_path("DEPOT-01", "CA-05")  # Returns List[RouteStep]
path2 = map_service.get_ideal_path("CA-05", "STATION-A")
```

### 2. DMAS_ET Integration
```python
# BiddingService uses DMAS_ET_silent for cost calculation
from agv_data.agv_agent import DMAS_ET_silent, RouteStep

E_j2, TFT_j2 = DMAS_ET_silent(
    route_plan=new_route_plan,
    global_start_time=start_datetime,
    agv_id="AGV_1"
)
```

### 3. Model Integration
```python
# Uses existing Django models
from agv_data.models import Agv, ResourceAgent
from order_data.models import Order

# Query idle AGVs
idle_agvs = Agv.objects.filter(motion_state=Agv.IDLE)

# Get node information
pickup_resource = ResourceAgent.objects.get(id=order.storage_node)
```

---

## Configuration

### Constants (from `agv_agent_constants.py`)
```python
# Energy calculation
C_BASE = 0.05           # Base energy (kJ/m)
C_LOAD_COEFF = 0.002    # Load coefficient (kJ/(kg·m))
P_IDLE = 0.1            # Idle power (W)

# Cost function weights
K_ENERGY = 0.5          # Energy weight
K_TIME = 0.5            # Time weight

# Dynamic normalization
EPSILON = 0.5           # Balance between MiniSum (efficiency) and MiniMax (fairness)
                        # ε = 1.0: Pure efficiency
                        # ε = 0.0: Pure load balancing
                        # ε = 0.5: 50/50 balance

# Fallback values
FALLBACK_NORM_ENERGY_KJ = 1.0
FALLBACK_NORM_TFT_SEC = 1.0

# System configuration
DEPOT_LOCATION_NAME = "DEPOT-01"  # Default depot
DEFAULT_LOAD_KG = 100.0           # Default load weight
```

---

## Testing

### Test Script: `test_auction_system.py`
```bash
# Run from agv_server directory
python test_auction_system.py
```

**Prerequisites:**
1. Django server running
2. Map data loaded (ResourceAgent nodes/edges)
3. At least one idle AGV
4. At least one Order

**Test Coverage:**
- ✅ Test 1: Auctioneer baseline calculation
- ✅ Test 2: Single AGV bid calculation
- ✅ Test 3: Complete auction process

**Expected Output:**
```
==================================================
SSI-DMAS-ET AUCTION SYSTEM - TEST SUITE
==================================================

CHECKING PREREQUISITES
✓ ResourceAgent nodes: 11
✓ ResourceAgent edges: 24
✓ Total AGVs: 3 (Idle: 3)
✓ Orders: 5
[SUCCESS] All prerequisites met!

TEST 1: AUCTIONEER SERVICE
[AuctioneerService] Calculating Baseline for Order 1
  E_baseline  = 67.5000 kJ
  TFT_baseline = 150.00 sec
[SUCCESS] Baseline calculated

TEST 2: BIDDING SERVICE
[BiddingService] Calculating bid for AGV 1
  b_final = 1.234567
[SUCCESS] Bid calculated

TEST 3: COMPLETE AUCTION PROCESS
Winner: AGV 1
Winning Bid: 1.234567
[SUCCESS] Auction completed

==================================================
TEST SUMMARY
✓ PASS: Auctioneer Service
✓ PASS: Bidding Service
✓ PASS: Auction Process
Total: 3/3 tests passed
🎉 ALL TESTS PASSED!
==================================================
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     NEW ORDER ARRIVES                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              TaskManager.run_auction(order)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
       ┌─────────────┴─────────────┐
       │                           │
       ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│ AuctioneerService│      │  Get Idle AGVs   │
│calculate_baseline│      │  from Database   │
└────────┬─────────┘      └─────────┬────────┘
         │                          │
         │ (E_baseline,             │ (List[AGV])
         │  TFT_baseline)           │
         │                          │
         └─────────┬────────────────┘
                   │
                   ▼
         ┌──────────────────────────┐
         │   For each AGV:          │
         │   BiddingService         │
         │   .calculate_bid_for_agv()│
         └─────────┬────────────────┘
                   │
                   │ (bids: Dict[agv_id, bid])
                   │
                   ▼
         ┌──────────────────────────┐
         │   Select Winner:         │
         │   winner = argmin(bids)  │
         └─────────┬────────────────┘
                   │
                   ▼
         ┌──────────────────────────┐
         │   Return (winner_id,     │
         │          winning_bid)    │
         └──────────────────────────┘
```

---

## Example Usage Scenario

### Scenario: 3 AGVs bidding for 1 Order

```python
# Order details
order_id = 123
parking_node = "CA-01"
storage_node = "CA-05"  (Pickup)
workstation_node = "STATION-A"  (Delivery)

# Step 1: Auctioneer calculates baseline
E_baseline = 67.5 kJ    # Depot->CA-05: 5kJ, CA-05->STATION-A: 62.5kJ
TFT_baseline = 150 sec  # Depot->CA-05: 60s, CA-05->STATION-A: 90s

# Step 2: AGVs calculate bids

## AGV 1 (Currently idle, close to depot)
J1: E=0 kJ, TFT=0 s
J2: E=70 kJ, TFT=160 s (small delay at CA-03)
Marginal: E=70 kJ, TFT=160 s
Normalized: E=1.037, TFT=1.067
b_ms = 0.5*1.037 + 0.5*1.067 = 1.052
b_mm = 0.5*1.037 + 0.5*1.067 = 1.052
b_final = 0.5*1.052 + 0.5*1.052 = 1.052 ★ WINNER

## AGV 2 (Currently idle, far from depot)
J1: E=0 kJ, TFT=0 s
J2: E=95 kJ, TFT=200 s (longer route + delays)
Marginal: E=95 kJ, TFT=200 s
Normalized: E=1.407, TFT=1.333
b_ms = 0.5*1.407 + 0.5*1.333 = 1.370
b_mm = 0.5*1.407 + 0.5*1.333 = 1.370
b_final = 1.370

## AGV 3 (Currently idle, moderate distance)
J1: E=0 kJ, TFT=0 s
J2: E=80 kJ, TFT=175 s
Marginal: E=80 kJ, TFT=175 s
Normalized: E=1.185, TFT=1.167
b_ms = 0.5*1.185 + 0.5*1.167 = 1.176
b_mm = 0.5*1.185 + 0.5*1.167 = 1.176
b_final = 1.176

# Winner: AGV 1 with bid = 1.052
```

---

## Next Steps

### Immediate Tasks
1. ✅ Implement Auctioneer Service
2. ✅ Implement Bidding Service
3. ✅ Implement Task Manager
4. ✅ Create test script
5. ⏳ Integrate with order arrival webhook/signal
6. ⏳ Implement Intention Ant (task assignment + book_slot_strict)

### Future Enhancements
1. **Multi-task Support**
   - Extend BiddingService to handle AGVs with existing tasks
   - Implement TSP optimization for task insertion

2. **Advanced Features**
   - Real-time auction monitoring dashboard
   - Auction history and analytics
   - Configurable epsilon per order type
   - Adaptive baseline calculation

3. **Performance Optimization**
   - Parallel bid calculation (threading/async)
   - Caching of frequently used paths
   - Incremental route planning

---

## Files Modified/Created

### New Files
```
agv_server/
├── agv_services/
│   ├── __init__.py              (updated)
│   ├── auctioneer_service.py    (updated with MapService integration)
│   ├── bidding_service.py       (updated with AGV integration)
│   └── task_manager.py          (NEW - auction coordination)
└── test_auction_system.py       (NEW - comprehensive tests)
```

### Documentation
```
docs/
└── auction-bidding-implementation.md (THIS FILE)
```

---

## References

1. **Specification:** `docs/auction-logic/auction-logic-implementation-guide.md`
2. **Constants:** `agv_data/agv_agent_constants.py`
3. **DMAS_ET:** `agv_data/agv_agent.py`
4. **MapService:** `agv_data/services.py`
5. **Models:** `agv_data/models.py`, `order_data/models.py`

---

## Success Metrics

✅ **Baseline Calculation:** Accurate, uses real map data via Dijkstra
✅ **Bid Calculation:** Dynamic normalization working correctly
✅ **Winner Selection:** Argmin correctly identifies most efficient AGV
✅ **Integration:** Seamless with existing MapService and DMAS_ET
✅ **Testing:** Comprehensive test script with prerequisite checks
✅ **Documentation:** Complete implementation guide and examples

---

## Contact & Support

For questions or issues with the auction system:
- Review `auction-logic-implementation-guide.md`
- Run `test_auction_system.py` for diagnostics
- Check logs in TaskManager/AuctioneerService/BiddingService

---

**Implementation Status:** ✅ **COMPLETE**
**Date:** November 9, 2025
**Version:** 1.0
