# AGV Model Refactoring for SSI-DMAS-ET

**Date:** November 28, 2025  
**Branch:** `refractor/reservation_table`  
**Version:** 2.0

---

## 📋 Overview

This document explains the refactoring of the `Agv` model from **DSPA algorithm** to **SSI-DMAS-ET system**.

### Algorithm Migration

| Old System | New System |
|------------|------------|
| **DSPA** (Dynamic Scheduling & Path Allocation) | **SSI-DMAS-ET** (Sequential Single-Item Auction with DMAS + Energy-Time) |
| Path planning with deadlock resolution | Auction-based task allocation |
| Common nodes & backup nodes | Reservation Table for conflict-free allocation |
| Spare flag for deadlock avoidance | DMAS-ET exploring ant for cost calculation |

---

## 🔄 Refactoring Summary

### ✅ Fields KEPT (Used by SSI-DMAS-ET)

| Field | Purpose | Usage in SSI-DMAS-ET |
|-------|---------|----------------------|
| `agv_id` | Primary key | AGV identification |
| `preferred_parking_node` | Parking location | Baseline calculation in auction |
| `current_node` | Current position | Start point for route planning |
| `next_node` | Next destination | Navigation tracking |
| `reserved_node` | Booked node | Reservation Table integration |
| `previous_node` | Last visited | Direction calculation |
| `direction_change` | Turn direction | Physical AGV control |
| `motion_state` | IDLE/MOVING/WAITING | State machine |
| `journey_phase` | OUTBOUND/INBOUND | **Load weight calculation in energy model** |
| `active_order` | Current task | Winner assignment after auction |
| `remaining_path` | Remaining nodes | **J1 cost calculation for busy AGVs** |

### ⚠️ Fields DEPRECATED (Not used by SSI-DMAS-ET)

| Field | Original Purpose (DSPA) | Why Not Needed |
|-------|-------------------------|----------------|
| `spare_flag` | Deadlock resolution indicator | **Replaced by Reservation Table** |
| `backup_nodes` | Backup nodes for deadlock | **Reservation Table prevents deadlocks** |
| `waiting_for_deadlock_resolution` | Deadlock state tracking | **No deadlock in SSI-DMAS-ET** |
| `deadlock_partner_agv_id` | Partner in head-on deadlock | **No head-on conflicts** |
| `initial_path` | Fixed path from Algorithm 1 | **Dynamic route planning (MapService)** |
| `outbound_path` | Parking → workstation path | **Routes calculated per auction** |
| `inbound_path` | Workstation → parking path | **Routes calculated per auction** |
| `common_nodes` | Shared nodes with other AGVs | **Reservation Table handles sharing** |
| `adjacent_common_nodes` | Sequential shared nodes | **Not needed with reservations** |

**Note:** Deprecated fields are marked with `[DEPRECATED]` in help text and kept for backward compatibility. They can be removed in a future migration after confirming no dependencies.

---

## 🎯 Key Changes Explained

### 1. Journey Phase (`journey_phase`)

**Status:** ✅ KEPT

**Why?** Used in `BiddingService` for **load weight calculation**:

```python
# In agv_services/bidding_service.py
if agv.journey_phase == 0:  # OUTBOUND
    load_kg = DEFAULT_LOAD_KG  # Carrying goods
else:  # INBOUND
    load_kg = 0.0  # Empty return
```

**Energy Formula:**
```
E_travel = (C_BASE + C_LOAD_COEFF × load_kg) × distance_m
```

- OUTBOUND: AGV may carry load (parking → storage → workstation)
- INBOUND: AGV is empty (workstation → parking)

**Impact:** Critical for accurate energy cost calculation in bidding.

---

### 2. Remaining Path (`remaining_path`)

**Status:** ✅ KEPT

**Why?** Used for **J1 calculation in busy AGVs**:

```python
# In agv_services/bidding_service.py
def calculate_J1_for_busy_agv(agv):
    """Calculate cost of current schedule (J1)"""
    # Convert remaining_path to RouteSteps
    route_j1 = []
    for node_num in agv.remaining_path:
        # Get LSA from ResourceAgent
        step = RouteStep(from_node, to_node, distance_m, duration_sec, ...)
        route_j1.append(step)
    
    # Calculate J1 using DMAS-ET
    (E_j1, TFT_j1) = DMAS_ET_silent(route_j1, start_time, agv_id)
    return (E_j1, TFT_j1)
```

**Auction Flow:**
1. **Idle AGV:** `remaining_path = []` → `J1 = (0, 0)`
2. **Busy AGV:** `remaining_path = [9, 10, 11]` → `J1 = cost(complete current task)`
3. **Marginal Cost:** `J2 - J1` = additional cost of new task

**Impact:** Enables fair comparison between idle and busy AGVs (task chaining).

---

### 3. DSPA Fields (All Deprecated)

**Status:** ⚠️ DEPRECATED (kept for backward compatibility)

**Why Removed?**

#### A. `spare_flag`, `backup_nodes`, `deadlock_*` fields

**DSPA Approach:**
- Detect shared nodes between AGV paths
- Allocate backup nodes for deadlock avoidance
- Move AGVs to backup when conflict detected

**SSI-DMAS-ET Approach:**
- **Reservation Table** reserves time slots
- Query `query_slot` returns earliest available time
- Book `book_slot_strict` ensures no conflicts
- **No deadlocks possible** (temporal separation)

```python
# Old DSPA (complex deadlock logic):
if spare_flag and is_shared_node(node):
    backup = backup_nodes[node]
    move_to_backup(backup)
    wait_for_partner()

# New SSI-DMAS-ET (simple reservation):
earliest_time = query_slot(resource_id, arrival_time, duration)
if earliest_time > arrival_time:
    wait_energy = calculate_wait_energy(delay)
book_slot(resource_id, start_time, end_time)  # Guaranteed conflict-free
```

#### B. `initial_path`, `outbound_path`, `inbound_path`

**DSPA Approach:**
- Path calculated once by Algorithm 1
- Fixed path stored in database
- Path doesn't change during execution

**SSI-DMAS-ET Approach:**
- **Dynamic route planning** per auction
- `MapService.get_ideal_path(start, end)` calculates fresh route
- Routes can change based on:
  - Current AGV position
  - Task requirements (storage, workstation)
  - Real-time reservation conflicts

```python
# Old DSPA (fixed paths):
initial_path = [1, 5, 10, 15, 20]  # Never changes
outbound_path = [1, 5, 10]
inbound_path = [10, 5, 1]

# New SSI-DMAS-ET (dynamic planning):
# For each auction:
route = MapService.get_ideal_path(agv.current_node, storage_node)
route += MapService.get_ideal_path(storage_node, workstation_node)
# Fresh calculation every time!
```

#### C. `common_nodes`, `adjacent_common_nodes`

**DSPA Approach:**
- Pre-calculate shared nodes between all AGV pairs
- Track sequential shared points (SCP)
- Complex conflict detection algorithm

**SSI-DMAS-ET Approach:**
- **Reservation Table** is single source of truth
- Resources are either free or occupied
- No need to track which AGVs share which nodes

```python
# Old DSPA (complex intersection logic):
common_nodes = path_a ∩ path_b ∩ path_c
adjacent_common_nodes = filter_sequential(common_nodes)
if next_node in adjacent_common_nodes:
    check_spare_flag()

# New SSI-DMAS-ET (simple time-based check):
result = query_slot(resource_id, arrival_time, duration)
# That's it! Reservation Table handles everything
```

---

## 🏗️ Architecture Impact

### Before (DSPA)

```
AGV Model (Complex)
├── Path Planning Fields (initial_path, outbound_path, inbound_path)
├── Deadlock Fields (spare_flag, backup_nodes, deadlock_partner)
├── Conflict Detection Fields (common_nodes, adjacent_common_nodes)
└── Control Policy Fields (motion_state, journey_phase)

Control Flow:
1. Calculate fixed paths (Algorithm 1)
2. Store paths in database
3. Detect common nodes between AGVs
4. Allocate backup nodes
5. Execute with deadlock resolution logic
```

### After (SSI-DMAS-ET)

```
AGV Model (Simple)
├── Navigation Fields (current_node, next_node, reserved_node)
├── State Fields (motion_state, journey_phase)
├── Task Fields (active_order, remaining_path)
└── DEPRECATED Fields (for backward compatibility)

Control Flow:
1. Auction allocates task to winner AGV
2. Winner calculates route dynamically (MapService)
3. Winner reserves slots (Reservation Table)
4. Winner executes task (no deadlock possible)
```

**Complexity Reduction:**
- ❌ No path storage
- ❌ No deadlock logic
- ❌ No shared node tracking
- ✅ Simple reservation API
- ✅ Dynamic route planning
- ✅ Temporal conflict avoidance

---

## 📊 Database Migration Strategy

### Current State (v2.0)

Fields are **marked deprecated** but **not removed**.

```python
# models.py
spare_flag = models.BooleanField(
    default=False,
    help_text="[DEPRECATED] DSPA spare flag - not used in SSI-DMAS-ET",
)
```

### Why Keep Deprecated Fields?

1. **Backward Compatibility:** Existing code that reads these fields won't break
2. **Data Preservation:** Historical AGV data in database is preserved
3. **Gradual Migration:** Views/serializers can be updated incrementally
4. **Risk Mitigation:** Easy rollback if issues found

### Future Migration (v3.0)

**Step 1:** Verify no code depends on deprecated fields
```bash
# Check for usage
grep -r "spare_flag" agv_server/
grep -r "backup_nodes" agv_server/
grep -r "common_nodes" agv_server/
```

**Step 2:** Create migration to remove fields
```python
# migrations/000X_remove_deprecated_dspa_fields.py
operations = [
    migrations.RemoveField(model_name='agv', name='spare_flag'),
    migrations.RemoveField(model_name='agv', name='backup_nodes'),
    migrations.RemoveField(model_name='agv', name='waiting_for_deadlock_resolution'),
    migrations.RemoveField(model_name='agv', name='deadlock_partner_agv_id'),
    migrations.RemoveField(model_name='agv', name='initial_path'),
    migrations.RemoveField(model_name='agv', name='outbound_path'),
    migrations.RemoveField(model_name='agv', name='inbound_path'),
    migrations.RemoveField(model_name='agv', name='common_nodes'),
    migrations.RemoveField(model_name='agv', name='adjacent_common_nodes'),
]
```

**Step 3:** Update reset functions
```python
# order_data/views.py, agv_data/views.py
def _reset_agv(self, agv):
    agv.current_node = None
    agv.next_node = None
    agv.reserved_node = None
    agv.motion_state = Agv.IDLE
    agv.remaining_path = []
    agv.active_order = None
    # Remove: spare_flag, backup_nodes, common_nodes, etc.
    agv.save()
```

---

## 🔍 Code Dependencies

### Files Currently Using Deprecated Fields

**1. order_data/views.py**
```python
# In _reset_agv()
agv.spare_flag = False  # ⚠️ DEPRECATED
agv.backup_nodes = {}  # ⚠️ DEPRECATED
agv.common_nodes = []  # ⚠️ DEPRECATED
agv.adjacent_common_nodes = []  # ⚠️ DEPRECATED
```

**2. agv_data/views.py**
```python
# In ResetAllAGVsView
agv.spare_flag = False  # ⚠️ DEPRECATED
agv.backup_nodes = {}  # ⚠️ DEPRECATED
agv.common_nodes = []  # ⚠️ DEPRECATED
agv.adjacent_common_nodes = []  # ⚠️ DEPRECATED

# In AgvListView (statistics)
"common_nodes_count": len(agv.common_nodes)  # ⚠️ DEPRECATED
"adjacent_common_nodes_count": len(agv.adjacent_common_nodes)  # ⚠️ DEPRECATED
```

**Action Items:**
- ✅ Keep for now (v2.0) - backward compatible
- ⏳ Remove in v3.0 after verification

---

## 🎯 Verification Checklist

### ✅ Completed (v2.0)

- [x] Model refactored with clear comments
- [x] Deprecated fields marked with `[DEPRECATED]` help text
- [x] Documentation created (this file)
- [x] Core SSI-DMAS-ET fields identified
- [x] Usage of `journey_phase` explained
- [x] Usage of `remaining_path` explained

### ⏳ Pending (v3.0)

- [ ] Verify auction system works with refactored model
- [ ] Update `_reset_agv()` functions to skip deprecated fields
- [ ] Update serializers to exclude deprecated fields from API responses
- [ ] Remove deprecated field usage from views
- [ ] Create migration to drop deprecated columns
- [ ] Update all documentation references

---

## 📚 Related Documentation

- [`DMAS-ET-OVERVIEW.md`](./DMAS-ET-OVERVIEW.md) - SSI-DMAS-ET system architecture
- [`auction-logic/`](./auction-logic/) - Auction system documentation
- [`database-schema.md`](./database-schema.md) - Database schema (needs update)
- [`reservation-table/`](./reservation-table/) - Reservation Table API

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Nov 28, 2025 | Initial refactoring - deprecated DSPA fields, kept SSI-DMAS-ET fields |
| 3.0 | TBD | Planned removal of deprecated fields |

---

## 🎓 Key Takeaways

### 1. SSI-DMAS-ET is Simpler than DSPA

**DSPA:**
- 9 deprecated fields for complex deadlock logic
- Fixed paths stored in database
- Shared node tracking between AGVs
- Backup node allocation

**SSI-DMAS-ET:**
- 2 critical fields: `journey_phase`, `remaining_path`
- Dynamic route planning (MapService)
- Temporal reservation (Reservation Table)
- No deadlock possible

### 2. Reservation Table Replaces DSPA Conflict Logic

| DSPA Mechanism | SSI-DMAS-ET Replacement |
|----------------|------------------------|
| `spare_flag` + `backup_nodes` | `query_slot()` + `book_slot()` |
| `common_nodes` detection | Time-based slot checking |
| `waiting_for_deadlock_resolution` | Wait energy calculation |
| Complex Algorithm 3 | Simple API calls |

### 3. Journey Phase Has New Purpose

**DSPA:** Track outbound/inbound for path selection  
**SSI-DMAS-ET:** Determine load weight for energy calculation

**Critical for auction fairness:**
- Loaded AGV (OUTBOUND): Higher energy bid
- Empty AGV (INBOUND): Lower energy bid

### 4. Remaining Path Enables Task Chaining

**Without `remaining_path`:**
- Busy AGVs can't participate in auctions
- Only idle AGVs bid
- Poor resource utilization

**With `remaining_path`:**
- Busy AGVs calculate marginal cost (J2 - J1)
- Nearby busy AGV can win if marginal cost is low
- Optimal task chaining discovered automatically

---

**Last Updated:** November 28, 2025  
**Author:** Development Team  
**Status:** ✅ v2.0 Complete, ⏳ v3.0 Planned

---
