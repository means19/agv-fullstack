# SSI-DMAS-ET System Overview

**Sequential Single-Item Auction with Degelated Multi-Agent System and Energy-Time Optimization**

**Date:** November 9, 2025  
**Version:** 1.2  

---

## 📋 Table of Contents

1. [System Architecture](#-system-architecture)
2. [Core Components](#-core-components)
3. [Implementation Status](#-implementation-status)
4. [Algorithm Flow](#-algorithm-flow)
5. [Key Concepts](#-key-concepts)
6. [Documentation Map](#-documentation-map)
7. [Development Roadmap](#-development-roadmap)

---

## 🏗️ System Architecture

The SSI-DMAS-ET system is a **multi-agent auction-based task allocation system** for AGVs with three main phases:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSI-DMAS-ET SYSTEM                           │
└─────────────────────────────────────────────────────────────────┘

Phase 1: AUCTION (Task Allocation Decision)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Order Arrives
         │
         ▼
    ┌─────────────┐
    │ Auctioneer  │ ──> Calculate Baseline (parking → storage → workstation)
    └─────────────┘     Uses: MapService (Dijkstra)
         │              Returns: (E_baseline, TFT_baseline)
         │
         ▼
    ┌─────────────┐
    │ All AGVs    │ ──> Each AGV calculates Bid
    │ Bid         │     - J1: Cost for current schedule (if busy)
    └─────────────┘     - J2: Cost for current + new task
         │              - Marginal: J2 - J1
         │              - Normalize by baseline
         │              - b_final = ε·b_ms + (1-ε)·b_mm
         │
         ▼
    ┌─────────────┐
    │ Winner      │ ──> argmin(bids)
    │ Selection   │     Winner gets task assignment
    └─────────────┘
         │
         ▼

Phase 2: EXPLORING ANT (Route Planning & Cost Calculation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ┌─────────────┐
    │ DMAS-ET     │ ──> Simulate AGV journey on planned route
    │ (Exploring) │     For each step:
    └─────────────┘       1. Query Reservation Table (earliest free slot)
         │                2. Calculate delay (wait if occupied)
         │                3. Calculate energy (travel + wait)
         │                4. Track TFT (Total Flow Time)
         │              Returns: (E_total, TFT_total)
         │              Uses: Reservation Table API (query_slot)
         │
         ▼

Phase 3: INTENTION ANT (Reservation & Execution) [⏳ PENDING]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ┌─────────────┐
    │ Book Slots  │ ──> Reserve exact time slots
    │ (Intention) │     For each step:
    └─────────────┘       1. Call book_slot_strict
         │                2. Handle conflicts (409 → replan)
         │                3. Transaction rollback on failure
         │              Uses: Reservation Table API (book_slot)
         │
         ▼
    ┌─────────────┐
    │ Execute     │ ──> AGV follows reserved path
    │ Task        │     Real-time execution
    └─────────────┘
```

---

## 🧩 Core Components

### 1. **Auction System** 

Handles task allocation through competitive bidding.

#### Components:
- **AuctioneerService**: Calculates baseline costs for normalization
- **BiddingService**: Calculates AGV bids using marginal costs
- **TaskManager**: Orchestrates complete auction process

#### Key Features:
- ✅ Dynamic baseline normalization (scale-free bid comparison)
- ✅ Hybrid MiniSum/MiniMax objective (efficiency + fairness)
- ✅ Support for idle and busy AGVs
- ✅ Marginal cost calculation (J2 - J1)
- ✅ Direct route planning (no parking detour)

**Documentation:** [`docs/auction-logic/`](./auction-logic/)

---

### 2. **Exploring Ant (DMAS-ET)** 

Simulates AGV journey and calculates costs without making reservations.

#### Algorithm:
```python
def DMAS_ET_silent(route_plan, global_start_time, agv_id):
    """
    Simulate AGV journey through planned route.
    
    Returns:
        (E_total, TFT_total): Raw costs (energy kJ, time seconds)
        (inf, inf): If route is infeasible
    """
    total_energy = 0.0
    total_tft = 0.0
    current_time = global_start_time
    
    for step in route_plan:
        # 1. Query Reservation Table (when can I enter this resource?)
        earliest_time = query_slot_api(
            from_node, to_node, 
            arrival_time=current_time,
            duration_sec=step.duration_sec
        )
        
        # 2. Calculate delay
        delay = max(0, earliest_time - current_time)
        wait_energy = delay * POWER_IDLE_KW / 3600
        
        # 3. Calculate travel energy
        travel_energy = calculate_energy(step.distance_m, step.load_kg)
        
        # 4. Update state
        total_energy += wait_energy + travel_energy
        current_time = earliest_time + step.duration_sec
        
        # 5. Track TFT (if this is task endpoint)
        if step.is_task_endpoint:
            total_tft = (current_time - global_start_time).total_seconds()
    
    return (total_energy, total_tft)
```

#### Key Features:
- ✅ Total Flow Time (TFT) metric instead of Sum of Tardiness (SOT)
- ✅ Raw cost output (no normalization at this layer)
- ✅ Conflict detection through reservation table queries
- ✅ Wait energy calculation during delays
- ✅ Load-dependent travel energy

**Documentation:** [`docs/exploring-ants/`](./exploring-ants/)

---

### 3. **Reservation Table** 

Manages time-based resource reservations for conflict-free allocation.

#### APIs:

**A. Query Phase (Exploring Ant):**
```python
query_slot(resource_id, arrival_time, duration_sec)
# Returns: earliest_available_time
# Does NOT make reservation
```

**B. Booking Phase (Intention Ant):** [⏳ PENDING INTEGRATION]
```python
book_slot_strict(resource_id, start_time, end_time, agv_id)
# Returns: 200 OK (booked) or 409 Conflict (occupied)
# Makes actual reservation
# Transaction isolation ensures atomicity
```

#### Key Features:
- ✅ Strict booking policy (fail-fast on conflicts)
- ✅ Transaction isolation for multi-step bookings
- ✅ Query without reservation (exploring phase)
- ✅ Rollback on booking failure
- ✅ Time-based conflict detection

**Documentation:** [`docs/reservation-table/`](./reservation-table/)

---

### 4. **Map Service** 

Provides graph-based pathfinding using Dijkstra algorithm.

#### Functions:
```python
MapService.get_ideal_path(start_node, end_node)
# Returns: List[RouteStep] with distances and travel times
# Uses: NetworkX Dijkstra on ResourceAgent graph
```

#### Key Features:
- ✅ NetworkX graph from ResourceAgent database
- ✅ Dijkstra shortest path calculation
- ✅ Distance and travel time estimation
- ✅ 248 ResourceAgent records (48 CA nodes, 188 LSA edges)

**Documentation:** [`docs/map-service/`](./map-service/)

---

## ✅ Implementation Status

| Component | Status | Features | Pending |
|-----------|--------|----------|---------|
| **Auction System** | 🟢 Complete | Baseline, Bidding, Winner Selection | Order arrival trigger |
| **Exploring Ant (DMAS-ET)** | 🟢 Complete | TFT metric, Energy calc, Query API | - |
| **Reservation Table** | 🟢 Complete | Query API, Book API, Transactions | - |
| **Map Service** | 🟢 Complete | Dijkstra, RouteStep generation | - |
| **Intention Ant** | 🔴 Not Started | - | Full implementation |
| **Task Execution** | 🔴 Not Started | - | Real-time control |
| **TSP Optimization** | 🔴 Not Started | - | Multi-task insertion |

### Test Status
| Test Suite | Status | Coverage |
|------------|--------|----------|
| Auction Tests | ✅ Passing | Baseline, Bidding, Complete auction |
| DMAS-ET Tests | ✅ Passing | Energy calc, TFT calc, Conflicts |
| Reservation Tests | ✅ Passing | Query, Book, Rollback |
| Integration Tests | ✅ Passing | End-to-end auction flow |

---

## 🔄 Algorithm Flow

### Complete Task Allocation Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. ORDER ARRIVAL                                             │
└──────────────────────────────────────────────────────────────┘
    Order(parking=1, storage=5, workstation=10) arrives
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. AUCTIONEER: Calculate Baseline                           │
└──────────────────────────────────────────────────────────────┘
    route = [1 → 5] + [5 → 10]  (from parking)
    (E_baseline, TFT_baseline) = DMAS_ET_silent(route)
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. BIDDING: Each AGV Calculates Bid                         │
└──────────────────────────────────────────────────────────────┘
    For AGV i:
    
    ┌─────────────────────────────────────────────────────┐
    │ Step 3.1: Calculate J1 (current schedule cost)     │
    └─────────────────────────────────────────────────────┘
        IF AGV is IDLE:
            (E_j1, TFT_j1) = (0, 0)
        ELSE (BUSY):
            route_j1 = remaining_path
            (E_j1, TFT_j1) = DMAS_ET_silent(route_j1)
    
    ┌─────────────────────────────────────────────────────┐
    │ Step 3.2: Create route for new task                │
    └─────────────────────────────────────────────────────┘
        IF IDLE:
            start = current_node
        ELSE:
            start = completion_node (last node in remaining_path)
        
        route_j2 = [start → storage] + [storage → workstation]
        
    ┌─────────────────────────────────────────────────────┐
    │ Step 3.3: Calculate J2 (current + new cost)        │
    └─────────────────────────────────────────────────────┘
        (E_j2, TFT_j2) = DMAS_ET_silent(route_j2)
    
    ┌─────────────────────────────────────────────────────┐
    │ Step 3.4: Calculate marginal cost                  │
    └─────────────────────────────────────────────────────┘
        E_marginal = E_j2 - E_j1
        TFT_marginal = TFT_j2 - TFT_j1
    
    ┌─────────────────────────────────────────────────────┐
    │ Step 3.5: Normalize by baseline                    │
    └─────────────────────────────────────────────────────┘
        E_norm_marginal = E_marginal / E_baseline
        TFT_norm_marginal = TFT_marginal / TFT_baseline
        
        E_norm_total = E_j2 / E_baseline
        TFT_norm_total = TFT_j2 / TFT_baseline
    
    ┌─────────────────────────────────────────────────────┐
    │ Step 3.6: Calculate hybrid bid                     │
    └─────────────────────────────────────────────────────┘
        b_ms = K_ENERGY * E_norm_marginal + K_TIME * TFT_norm_marginal
        b_mm = K_ENERGY * E_norm_total + K_TIME * TFT_norm_total
        
        b_final = ε * b_ms + (1-ε) * b_mm
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. WINNER SELECTION                                          │
└──────────────────────────────────────────────────────────────┘
    winner = argmin(b_final_i for all AGVs)
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. TASK ASSIGNMENT [⏳ PENDING]                              │
└──────────────────────────────────────────────────────────────┘
    Assign task to winner
    Update winner's schedule
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. INTENTION ANT: Book Reservations [⏳ PENDING]             │
└──────────────────────────────────────────────────────────────┘
    For each step in winner's route:
        result = book_slot_strict(resource_id, start_time, end_time)
        
        IF result == 409 Conflict:
            Rollback all bookings
            Replan route
            Retry booking
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. TASK EXECUTION [⏳ PENDING]                               │
└──────────────────────────────────────────────────────────────┘
    AGV follows reserved path
    Release slots after traversal
```

---

## 💡 Key Concepts

### 1. **Dynamic Baseline Normalization**

**Problem:** Different tasks have different scales (short vs long distances).

**Solution:** Normalize all costs by a task-specific baseline.

```python
# Without normalization:
Task A: bid = 10 kJ  (short task, 10 kJ is bad)
Task B: bid = 50 kJ  (long task, 50 kJ might be good)
# Can't compare directly!

# With dynamic normalization:
Task A: bid = 10/5 = 2.0  (200% of baseline = bad)
Task B: bid = 50/60 = 0.83  (83% of baseline = good)
# Now comparable!
```

**Baseline Calculation:**
```
Baseline = Ideal cost from parking node
         = Cost(parking → storage → workstation)
         = Reference for this specific task
```

**Documentation:** [`docs/tft-dynamic-normalization.md`](./tft-dynamic-normalization.md)

---

### 2. **Marginal Cost (J2 - J1)**

**Problem:** How to fairly compare idle AGVs vs busy AGVs?

**Solution:** Calculate the **additional (marginal) cost** of accepting a new task.

```python
# Idle AGV:
J1 = (0, 0)  # No current tasks
J2 = (15 kJ, 120s)  # New task cost
Marginal = J2 - J1 = (15 kJ, 120s)  # Full cost of new task

# Busy AGV (near new task):
J1 = (10 kJ, 60s)  # Complete current task
J2 = (15 kJ, 90s)  # Current + new task
Marginal = J2 - J1 = (5 kJ, 30s)  # Only additional cost! (Task chaining)

# Result: Busy AGV wins because marginal cost is lower!
```

**This enables "Task Chaining"** - System automatically discovers when a busy AGV can efficiently pick up a nearby task.

**Documentation:** [`docs/auction-logic/VERIFICATION_MARGINAL_COST.md`](./auction-logic/VERIFICATION_MARGINAL_COST.md)

---

### 3. **Hybrid Objective (MiniSum + MiniMax)**

**Problem:** Pure efficiency (MiniSum) can overload some AGVs. Pure fairness (MiniMax) can be inefficient.

**Solution:** Weighted combination controlled by ε (epsilon).

```python
b_ms = marginal cost (efficiency)  # Favors least additional effort
b_mm = total cost (fairness)       # Favors least loaded AGV

b_final = ε * b_ms + (1-ε) * b_mm

# ε = 1.0 → Pure MiniSum (efficiency)
# ε = 0.0 → Pure MiniMax (fairness)
# ε = 0.5 → Balanced (default)
```

**Tuning Guide:**
- High traffic → Lower ε (more fairness to prevent bottlenecks)
- Low traffic → Higher ε (more efficiency)

---

### 4. **Total Flow Time (TFT) vs Sum of Tardiness (SOT)**

**Problem:** SOT requires strict deadlines, returns 0 when all tasks are early.

**Solution:** Use TFT which measures total completion time.

| Metric | Formula | Use Case |
|--------|---------|----------|
| **SOT** | Σ max(0, t_i - d_i) | Strict deadlines, tardiness penalties |
| **TFT** | t_completion - t_start | Minimize makespan, no deadlines |

**Our System:** Uses TFT because tasks don't have strict deadlines.

**Documentation:** [`docs/tft-dynamic-normalization.md`](./tft-dynamic-normalization.md)

---

### 5. **Two-Phase Ant System**

**Exploring Ant (DMAS-ET):**
- ✅ Simulate journey (no reservations)
- ✅ Query reservation table (when can I enter?)
- ✅ Calculate costs (energy + TFT)
- ✅ Used in auction bidding phase

**Intention Ant:**
- ⏳ Book actual reservations (book_slot_strict)
- ⏳ Handle conflicts (409 → replan)
- ⏳ Transaction rollback on failure
- ⏳ Used after winning auction

**Why Two Phases?**
- Auction requires many cost calculations (N AGVs × M tasks)
- Only winner needs actual reservations
- Prevents reservation spam during bidding

---

## 📚 Documentation Map

```
docs/
├── DMAS-ET-OVERVIEW.md ⭐ (THIS FILE)
│   └── High-level system overview
│
├── auction-logic/ ✅ IMPLEMENTED
│   ├── README.md
│   │   └── Documentation index
│   ├── auction-bidding-implementation.md
│   │   └── Detailed implementation
│   ├── auction-bidding-quickstart.md
│   │   └── Quick start guide & testing
│   ├── INTEGRATION_VERIFICATION.md
│   │   └── Integration verification details
│   ├── VERIFICATION_MARGINAL_COST.md
│   │   └── Marginal cost verification
│   └── CHANGELOG.md
│       └── Version history
│
├── exploring-ants/ ✅ IMPLEMENTED
│   ├── agv-agent-exploring-ant.md
│   │   └── DMAS-ET algorithm details
│   ├── agv-agent-implementation-summary.md
│   │   └── Implementation summary
│   └── agv-agent-quickstart.md
│       └── Quick start & testing
│
├── reservation-table/ ✅ IMPLEMENTED
│   ├── reservation-table.md
│   │   └── API documentation
│   ├── reservation-table-implementation-summary.md
│   │   └── Implementation summary
│   └── reservation-table-quickstart.md
│       └── Quick start & usage
│
├── map-service/ ✅ IMPLEMENTED
│   ├── map-implementation-completed.md
│   │   └── MapService implementation
│   ├── map-implementation-test-results.md
│   │   └── Test results
│   └── map-expansion-guide.md
│       └── Map expansion guide
│
├── tft-dynamic-normalization.md ✅ REFERENCE
│   └── TFT metric & normalization theory
│
├── database-schema.md 📋 REFERENCE
│   └── Database models
│
├── web-app-services.md 📋 REFERENCE
│   └── System architecture
│
└── local-dev.md 🛠️ REFERENCE
    └── Development environment setup
```

---

## 🗺️ Development Roadmap

### ✅ Phase 1: Foundation (COMPLETED)

**Goal:** Core infrastructure for auction system

- [x] Reservation Table (query + book APIs)
- [x] Map Service (Dijkstra pathfinding)
- [x] Exploring Ant (DMAS-ET with TFT)
- [x] Energy calculation model
- [x] ResourceAgent database (248 records)

**Date:** Completed November 2025

---

### ✅ Phase 2: Auction System (COMPLETED)

**Goal:** Task allocation through competitive bidding

- [x] AuctioneerService (baseline calculation)
- [x] BiddingService (marginal cost, normalization)
- [x] TaskManager (auction orchestration)
- [x] Idle AGV support (J1 = 0)
- [x] Busy AGV support (J1 from remaining_path)
- [x] Dynamic baseline normalization
- [x] Hybrid MiniSum/MiniMax objective
- [x] Integration testing (all passing)
- [x] Comprehensive documentation

**Date:** Completed November 9, 2025

---

### ⏳ Phase 3: Intention Ant (PENDING)

**Goal:** Actual reservation and task assignment

- [ ] Implement Intention Ant algorithm
- [ ] Integrate with book_slot_strict API
- [ ] Handle booking conflicts (409 response)
- [ ] Transaction rollback on failure
- [ ] Retry logic with replanning
- [ ] Update AGV schedule after booking
- [ ] Release slots after task completion

**Target:** Q1 2026

---

### ⏳ Phase 4: Task Execution (PENDING)

**Goal:** Real-time AGV control

- [ ] Task execution monitoring
- [ ] Real-time position tracking
- [ ] Dynamic replanning on delays
- [ ] Slot release after traversal
- [ ] Emergency handling
- [ ] Multi-AGV coordination

**Target:** Q2 2026

---

### ⏳ Phase 5: Advanced Features (PENDING)

**Goal:** Optimization and scalability

- [ ] TSP optimization for multi-task insertion
- [ ] Adaptive epsilon based on system load
- [ ] Multi-task simultaneous auctions
- [ ] Machine learning for baseline prediction
- [ ] Auction monitoring dashboard
- [ ] Auction history and analytics

**Target:** Q3 2026

---

## 🔧 Configuration

### System Parameters

```python
# Energy Model (agv_agent_constants.py)
C_BASE = 0.05           # Base energy consumption (kJ/m)
C_LOAD_COEFF = 0.002    # Load coefficient (kJ/(kg·m))
POWER_IDLE_KW = 0.1     # Idle power during wait (kW)

# Cost Weights
K_ENERGY = 0.5          # Energy importance (0-1)
K_TIME = 0.5            # Time importance (0-1)
# Note: K_ENERGY + K_TIME should = 1.0

# Hybrid Objective
EPSILON = 0.5           # MiniSum vs MiniMax balance
                        # 1.0 = pure efficiency
                        # 0.0 = pure fairness
                        # 0.5 = balanced

# System
MIN_DURATION_SEC = 1.0  # Minimum reservation duration
DEFAULT_LOAD_KG = 100.0 # Default load weight
```

### Tuning Recommendations

**For High Traffic Warehouses:**
- Lower EPSILON (0.3-0.4) → More fairness
- Prevents AGV overload

**For Low Traffic Warehouses:**
- Higher EPSILON (0.6-0.8) → More efficiency
- Minimizes total travel time

**For Energy-Critical Systems:**
- Higher K_ENERGY (0.7-0.8)
- Lower K_TIME (0.2-0.3)

**For Time-Critical Systems:**
- Higher K_TIME (0.7-0.8)
- Lower K_ENERGY (0.2-0.3)

---

## 🧪 Testing

### Run All Tests

```bash
# Auction system tests
docker compose exec server python test_auction_system.py

# Sample tests (3 scenarios)
docker compose exec server python sample-data/sample_test_1_idle_agvs.py
docker compose exec server python sample-data/sample_test_2_mixed_agvs.py
docker compose exec server python sample-data/sample_test_3_multiple_orders.py
```

### Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Auction System | 3 tests | ✅ All passing |
| Sample Scenarios | 3 tests | ✅ All passing |
| Integration | 6 tests | ✅ All passing |

**Total:** 12/12 tests passing ✅

---

## 🎯 Success Metrics

### Current Performance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Auction time (10 AGVs) | < 1s | ~0.5s | ✅ |
| Auction time (50 AGVs) | < 5s | TBD | ⏳ |
| Winner accuracy | 100% | 100% | ✅ |
| Integration tests | All pass | 12/12 | ✅ |
| Documentation coverage | 100% | 100% | ✅ |

### Key Achievements

✅ **Scale-free bidding** - Works for tasks of any size  
✅ **Task chaining** - Busy AGVs can win if nearby  
✅ **Conflict detection** - Routes avoid resource collisions  
✅ **Fair comparison** - Dynamic normalization ensures fairness  
✅ **Hybrid objective** - Balances efficiency and load distribution  

---

## 🚀 Quick Start

### 1. Setup Development Environment

```bash
# Start all services
./start-dev.ps1

# Check services
docker compose ps
```

### 2. Run Simple Auction Test

```bash
# Create test AGVs and order
docker compose exec server python sample-data/setup_test_agvs.py

# Run auction
docker compose exec server python test_auction_system.py
```

### 3. View Results

```
=== Test: Complete Auction ===

Baseline (from parking):
  E_baseline = 0.2625 kJ
  TFT_baseline = 315.0 sec

AGV 1 (IDLE): Bid = 1.142857
AGV 2 (BUSY): Bid = 0.916667 ← WINNER
AGV 3 (IDLE): Bid = 1.019048

Winner: AGV 2
Status: ✅ PASS
```

---

## 📞 Support & Contributing

### For Questions

1. Check this overview document
2. Check component-specific docs in respective folders
3. Review test files for usage examples

### For Development

1. Follow existing code structure
2. Write tests for new features
3. Update documentation
4. Run all tests before commit

### Documentation Updates

When implementing new features:

1. Update this overview (implementation status)
2. Update component-specific docs
3. Add examples to quickstart guides
4. Update roadmap and success metrics

---

## 📄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 2, 2025 | Initial foundation (Reservation, Map, DMAS-ET) |
| 1.1 | Nov 6, 2025 | Auction system complete, Busy AGV support |
| 1.2 | Nov 9, 2025 | Documentation reorganization, This overview created |

---

## 🎓 Key References

### Research Papers
<a id="1">[[1]](https://linkinghub.elsevier.com/retrieve/pii/S0278612521002429)</a> M. De Ryck, D. Pissoort, T. Holvoet, and E. Demeester, “Decentral task allocation for industrial AGV-systems with routing constraints,” Journal of Manufacturing Systems, vol. 62, pp. 135–144, Jan. 2022, doi: 10.1016/j.jmsy.2021.11.012.

<a id="2">[[2]](http://link.springer.com/10.1007/s00170-017-0915-8)</a> B. Micieta et al., “Delegate MASs for coordination and control of one-directional AGV systems: a proof-of-concept,” Int J Adv Manuf Technol, vol. 94, no. 1–4, pp. 415–431, Jan. 2018, doi: 10.1007/s00170-017-0915-8.

<a id="3">[[3]](https://www.mdpi.com/2076-3417/9/21/4515)</a> L. Ďurica, M. Gregor, V. Vavrík, M. Marschall, P. Grznár, and Š. Mozol, “A Route Planner Using a Delegate Multi-Agent System for a Modular Manufacturing Line: Proof of Concept,” Applied Sciences, vol. 9, no. 21, p. 4515, Oct. 2019, doi: 10.3390/app9214515.

<a id="4">[[4]](https://ieeexplore.ieee.org/document/10382354/)</a> H. A. Nguyen, D. M. Nguyen, Q. H. Pham, Q. D. Pham, and D. C. Hoang, “Energy and Time-Efficient Scheduling of Automated Guided Vehicles System: A Hybrid Artificial Bee Colony Algorithm and Improved Ant Colony Optimization Approach,” in 2023 12th International Conference on Control, Automation and Information Sciences (ICCAIS), Hanoi, Vietnam: IEEE, Nov. 2023, pp. 719–724. doi: 10.1109/ICCAIS59597.2023.10382354.

<a id="5">[[5]](http://link.springer.com/10.1007/978-3-540-71103-2_3)</a> T. Holvoet and P. Valckenaers, “Exploiting the Environment for Coordinating Agent Intentions,” in Environments for Multi-Agent Systems III, vol. 4389, D. Weyns, H. V. D. Parunak, and F. Michel, Eds., in Lecture Notes in Computer Science, vol. 4389. , Berlin, Heidelberg: Springer Berlin Heidelberg, 2007, pp. 51–66. doi: 10.1007/978-3-540-71103-2_3.


### Internal Docs
- [`tft-dynamic-normalization.md`](./tft-dynamic-normalization.md) - Theory
- [`auction-logic/`](./auction-logic/) - Implementation
- [`database-schema.md`](./database-schema.md) - Data models

### External Tools
- NetworkX (graph algorithms)
- Django (web framework)
- PostgreSQL (database)

---

**Last Updated:** November 9, 2025  
**System Status:** 🟢 Phase 2 Complete, Phase 3 Pending

---

