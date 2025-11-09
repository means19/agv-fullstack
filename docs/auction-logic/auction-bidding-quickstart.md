# Quick Start: Testing the Auction System

## Prerequisites

1. **Django server running**
   ```bash
   docker compose up -d
   ```

2. **Map data loaded**
   ```bash
   docker compose exec server python manage.py import_map
   ```

3. **Create test AGVs** (if not exists)
   
   **For testing with IDLE AGVs only:**
   ```bash
   docker compose exec server python manage.py shell
   ```
   ```python
   from agv_data.models import Agv
   
   # Create 3 idle AGVs at different locations
   agvs_data = [
       {"agv_id": 1, "current_node": 2},
       {"agv_id": 2, "current_node": 8},
       {"agv_id": 3, "current_node": 6},
   ]
   
   for data in agvs_data:
       Agv.objects.get_or_create(
           agv_id=data["agv_id"],
           defaults={
               'preferred_parking_node': 1,
               'motion_state': Agv.IDLE,
               'current_node': data["current_node"],
               'remaining_path': []
           }
       )
   ```

   **For testing with MIXED AGVs (idle + busy):**
   ```python
   from agv_data.models import Agv
   
   # AGV 1: IDLE at node 2
   Agv.objects.update_or_create(
       agv_id=1,
       defaults={
           'preferred_parking_node': 1,
           'motion_state': Agv.IDLE,
           'current_node': 2,
           'remaining_path': [],
           'journey_phase': 'EMPTY'
       }
   )
   
   # AGV 2: BUSY, currently at node 8, completing task to node 11
   Agv.objects.update_or_create(
       agv_id=2,
       defaults={
           'preferred_parking_node': 1,
           'motion_state': Agv.MOVING,
           'current_node': 8,
           'remaining_path': [
               {"from_node": 8, "to_node": 9},
               {"from_node": 9, "to_node": 10},
               {"from_node": 10, "to_node": 11}
           ],
           'journey_phase': 'LOADED',  # Will affect energy calculation
           'active_order_id': 999  # Some existing order
       }
   )
   
   # AGV 3: IDLE at node 6
   Agv.objects.update_or_create(
       agv_id=3,
       defaults={
           'preferred_parking_node': 1,
           'motion_state': Agv.IDLE,
           'current_node': 6,
           'remaining_path': [],
           'journey_phase': 'EMPTY'
       }
   )
   ```

4. **Create test order** (if not exists)
   ```bash
   docker compose exec server python manage.py shell
   ```
   ```python
   from order_data.models import Order
   from datetime import date, time
   
   Order.objects.get_or_create(
       order_id=1,
       defaults={
           'order_date': date.today(),
           'start_time': time(9, 0),
           'parking_node': 1,    # Baseline reference (e.g., CA-01)
           'storage_node': 5,    # Pickup location (e.g., CA-05)
           'workstation_node': 10, # Delivery location (e.g., CA-10)
           'weight_kg': 100.0    # Load weight
       }
   )
   ```
   
   **Note:** 
   - `parking_node`: Used as **ideal baseline reference** (not AGV start position)
   - AGVs route **directly** from their current/completion position to storage
   - NO parking detour for efficiency

## Run Tests

### Option 1: Run Full Test Suite
```bash
docker compose exec server python test_auction_system.py
```

### Option 2: Test Individual Components

**Test Auctioneer (Baseline Calculation):**
```bash
docker compose exec server python manage.py shell
```
```python
from agv_services import auctioneer_service
from order_data.models import Order

order = Order.objects.first()
E_baseline, TFT_baseline = auctioneer_service.calculate_baseline_from_order(order)
print(f"E_baseline: {E_baseline:.4f} kJ")
print(f"TFT_baseline: {TFT_baseline:.2f} sec")
# Note: Baseline calculated from parking node (ideal reference)
```

**Test Bidding (Single AGV - IDLE):**
```python
from agv_services import BiddingService
from agv_data.models import Agv

agv = Agv.objects.get(agv_id=1)  # Idle AGV
bidding_service = BiddingService()

bid = bidding_service.calculate_bid_for_agv(
    agv=agv,
    order=order,
    E_baseline=E_baseline,
    TFT_baseline=TFT_baseline
)
print(f"AGV {agv.agv_id} (IDLE) bid: {bid:.6f}")
# J1 = (0, 0) for idle AGV
# Route: current_node → storage → workstation
```

**Test Bidding (Single AGV - BUSY):**
```python
agv2 = Agv.objects.get(agv_id=2)  # Busy AGV
bid2 = bidding_service.calculate_bid_for_agv(
    agv=agv2,
    order=order,
    E_baseline=E_baseline,
    TFT_baseline=TFT_baseline
)
print(f"AGV {agv2.agv_id} (BUSY) bid: {bid2:.6f}")
# J1 calculated from remaining_path
# Route: completion_node → storage → workstation
```

**Test Complete Auction:**
```python
from agv_services import task_manager

result = task_manager.run_auction(order)
if result:
    winner_id, winning_bid = result
    print(f"Winner: AGV {winner_id}, Bid: {winning_bid:.6f}")
```

## Expected Output

```
==================================================
STARTING AUCTION FOR ORDER 1
==================================================
Parking: 1
Storage (Pickup): 5
Workstation (Delivery): 8
Start Time: 09:00:00

[Step 1] Auctioneer calculating baseline...
==================================================
[AuctioneerService] Calculating Baseline for Order 1
==================================================
Pickup: CA-05 (ID: 5)
Delivery: STATION-A (ID: 8)
Load: 100.0 kg

Leg 1: DEPOT-01 -> CA-05 (EMPTY)
  Distance: 100.00 m
  Time: 60.00 s
  Energy: 5.0000 kJ

Leg 2: CA-05 -> STATION-A (LOADED 100.0 kg)
  Distance: 150.00 m
  Time: 90.00 s
  Energy: 37.5000 kJ

==================================================
BASELINE RESULTS:
  E_baseline  = 42.5000 kJ
  TFT_baseline = 150.00 sec (2.50 min)
==================================================

✓ Baseline calculated successfully

[Step 2] Finding available AGVs...
✓ Found 3 idle AGVs

[Step 3] Collecting bids from AGVs...

--- AGV 1 ---
[BiddingService] Calculating bid for AGV 1
  Current costs (J1): E=0.000 kJ, TFT=0.0s
  Creating route plan for order...
    Route: CA-01 -> CA-05 -> STATION-A
  ✓ Route plan created with 8 steps
  Running DMAS_ET_silent to calculate J2...
  ✓ New costs (J2): E=44.500 kJ, TFT=155.0s
  Marginal costs: E=44.500 kJ, TFT=155.0s
  Normalized marginal: E=1.047, TFT=1.033
  Normalized total: E=1.047, TFT=1.033
  b_ms (MiniSum) = 1.040000
  b_mm (MiniMax) = 1.040000
  b_final = 1.040000
✓ AGV 1 bid: 1.040000

--- AGV 2 ---
[BiddingService] Calculating bid for AGV 2
  ...
✓ AGV 2 bid: 1.150000

--- AGV 3 ---
[BiddingService] Calculating bid for AGV 3
  ...
✓ AGV 3 bid: 1.080000

[Step 4] Selecting auction winner...

==================================================
AUCTION COMPLETED
==================================================
Winner: AGV 1
Winning Bid: 1.040000
Total Bidders: 3

All Bids:
  AGV 1: 1.040000 ★ WINNER
  AGV 3: 1.080000
  AGV 2: 1.150000
==================================================
```

## Troubleshooting

### Error: "No path found"
- **Cause:** Map data not loaded or incomplete
- **Fix:** Run `docker compose exec server python manage.py import_map`

### Error: "Resource not found"
- **Cause:** Order references invalid node IDs
- **Fix:** Check ResourceAgent IDs match Order's storage_node/workstation_node

### Error: "No idle AGVs"
- **Cause:** All AGVs are MOVING or WAITING
- **Fix:** Create idle AGVs or reset existing AGVs to IDLE state

### Error: "API call failed"
- **Cause:** Reservation Table API not responding
- **Fix:** Ensure Django server is running and accessible

### Bid returns `inf`
- **Cause:** No valid path or resource booking conflict
- **Fix:** Check map connectivity and reservation table availability

## Next Steps

After successful auction:
1. Implement task assignment (Intention Ant)
2. Implement resource booking (book_slot_strict)
3. Integrate with order arrival webhook
4. Add real-time monitoring dashboard

## Configuration

Edit constants in `agv_data/agv_agent_constants.py`:
```python
# Adjust energy/time weights
K_ENERGY = 0.5
K_TIME = 0.5

# Adjust MiniSum/MiniMax balance
EPSILON = 0.5  # 0.0=pure fairness, 1.0=pure efficiency

# Change depot location
DEPOT_LOCATION_NAME = "DEPOT-01"
```

## Documentation

- Full implementation: `docs/auction-logic/auction-bidding-implementation.md`
- Algorithm spec: `docs/auction-logic/auction-logic-implementation-guide.md`
- Constants: `agv_data/agv_agent_constants.py`
