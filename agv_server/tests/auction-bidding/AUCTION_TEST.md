# Sample Data - Auction System Testing

Thư mục này chứa các script mẫu để test auction system với các scenarios khác nhau.

---

## 📁 Available Sample Scripts

### 1. **sample_test_1_idle_agvs.py**
**Scenario:** Test auction với 3 AGVs đều IDLE

**Setup:**
- AGV 1: IDLE tại CA-02
- AGV 2: IDLE tại CA-08
- AGV 3: IDLE tại CA-06

**Order:**
- Parking: CA-01 (baseline reference)
- Storage: CA-05 (pickup)
- Workstation: CA-10 (delivery)

**Expected:**
- All 3 AGVs participate in bidding
- Winner: AGV closest to storage node
- All bids > 0

---

### 2. **sample_test_2_mixed_agvs.py**
**Scenario:** Test auction với mixed AGVs (2 idle + 1 busy)

**Setup:**
- AGV 1: IDLE tại CA-02
- AGV 2: **BUSY** tại CA-08, completing task to CA-11
  - Remaining path: CA-08 → CA-09 → CA-10 → CA-11
  - Journey phase: INBOUND (loaded, returning)
- AGV 3: IDLE tại CA-06

**Order:**
- Parking: CA-01
- Storage: CA-05
- Workstation: CA-10

**Expected:**
- All 3 AGVs can bid (busy AGV included!)
- Busy AGV calculates J1 from remaining_path
- Winner selected based on marginal cost (J2 - J1)
- May see busy AGV win if marginal cost is competitive

**Key Test:**
- Verifies busy AGV support
- Tests J1 calculation from remaining_path
- Tests route from completion_node

---

### 3. **sample_test_3_multiple_orders.py**
**Scenario:** Test auction với multiple orders sequentially

**Setup:**
- 3 idle AGVs at different locations

**Orders:**
1. Order 201: Near orders (storage=5, workstation=10)
2. Order 202: Far orders (storage=15, workstation=20)
3. Order 203: Short distance (storage=3, workstation=7)

**Expected:**
- Different winners for different orders
- Bids vary based on AGV position relative to order
- Summary table showing all results

---

## 🚀 How to Run

### Prerequisites
```powershell
# Ensure server is running
docker compose up -d

# Ensure map data is loaded
docker compose exec server python manage.py import_map
```

### Run Sample Tests

**Test 1: Idle AGVs**
```powershell
docker compose exec server python sample-data/sample_test_1_idle_agvs.py
```

**Test 2: Mixed AGVs (Idle + Busy)**
```powershell
docker compose exec server python sample-data/sample_test_2_mixed_agvs.py
```

**Test 3: Multiple Orders**
```powershell
docker compose exec server python sample-data/sample_test_3_multiple_orders.py
```

---

## 📊 Expected Output

### Test 1 Output Example:
```
======================================================================
SAMPLE TEST 1: AUCTION WITH 3 IDLE AGVs
======================================================================

[STEP 1] Setting up 3 idle AGVs at different locations...
  ✓ AGV 1: IDLE at CA-02
  ✓ AGV 2: IDLE at CA-08
  ✓ AGV 3: IDLE at CA-06

[STEP 2] Creating test order...
  ✓ Order 101: parking=1, storage=5, workstation=10

[STEP 3] Running auction...
----------------------------------------------------------------------
[Detailed auction output...]
----------------------------------------------------------------------

======================================================================
AUCTION RESULT
======================================================================
🏆 Winner: AGV 3
   Current Position: CA-06
   Winning Bid: 0.750625
   State: Idle
======================================================================

✅ SAMPLE TEST 1 COMPLETED SUCCESSFULLY!
```

### Test 2 Output Example:
```
======================================================================
SAMPLE TEST 2: AUCTION WITH MIXED AGVs (2 IDLE + 1 BUSY)
======================================================================

[STEP 1] Setting up 3 AGVs (2 idle + 1 busy)...
  ✓ AGV 1: IDLE at CA-02
  ✓ AGV 2: BUSY (MOVING) at CA-08, completing to CA-11
           Remaining path: CA-08 → CA-09 → CA-10 → CA-11
  ✓ AGV 3: IDLE at CA-06

[STEP 2] Creating test order...
  ✓ Order 102: parking=1, storage=5, workstation=10

[STEP 3] Running auction with mixed AGVs...
  Note: Busy AGV will calculate J1 from remaining_path
----------------------------------------------------------------------
[Detailed auction output with J1 calculation...]
----------------------------------------------------------------------

======================================================================
AUCTION RESULT
======================================================================
🏆 Winner: AGV 2
   Current Position: CA-08
   State: Moving
   Completion Node: CA-11
   Note: Bid calculated from completion position (marginal cost)
   Winning Bid: 0.916667
======================================================================

✅ SAMPLE TEST 2 COMPLETED SUCCESSFULLY!

Key Insight:
  → Busy AGV won! This shows marginal cost calculation working.
  → J1 (current task) was subtracted, showing only new task cost.
```

### Test 3 Output Example:
```
======================================================================
SAMPLE TEST 3: MULTIPLE ORDERS SEQUENTIAL AUCTION
======================================================================

[Detailed output for each order...]

======================================================================
AUCTION RESULTS SUMMARY
======================================================================
Order      Storage    Workstation  Winner     Bid            
----------------------------------------------------------------------
201        CA-05      CA-10        AGV 3      0.750625       
202        CA-15      CA-20        AGV 2      1.234567       
203        CA-03      CA-07        AGV 1      0.654321       
======================================================================

✅ SAMPLE TEST 3 COMPLETED: 3/3 auctions successful
```

---

## 🔍 What Each Test Validates

### Test 1 (Idle AGVs):
- ✅ Baseline calculation from parking node
- ✅ Direct routes (no parking detour)
- ✅ Idle AGV bidding (J1 = 0)
- ✅ MapService integration
- ✅ DMAS_ET integration
- ✅ Winner selection (argmin)

### Test 2 (Mixed AGVs):
- ✅ All of Test 1 features
- ✅ **Busy AGV detection**
- ✅ **J1 calculation from remaining_path**
- ✅ **Route from completion_node**
- ✅ **Marginal cost calculation (J2 - J1)**
- ✅ Competitive bidding with ongoing tasks

### Test 3 (Multiple Orders):
- ✅ All of Test 1 features
- ✅ **Multiple order handling**
- ✅ **Different bid values for different orders**
- ✅ **Winner varies based on position**
- ✅ System consistency across multiple auctions

---

## 🛠️ Customization

### Modify AGV Positions
Edit the `agvs_setup` list in scripts:
```python
agvs_setup = [
    {"agv_id": 1, "node": 2, "name": "CA-02"},
    {"agv_id": 2, "node": 8, "name": "CA-08"},
    {"agv_id": 3, "node": 6, "name": "CA-06"},  # Change node here
]
```

### Modify Order Locations
Edit the order creation:
```python
order = Order.objects.create(
    order_id=101,
    parking_node=1,      # Change parking reference
    storage_node=5,      # Change pickup location
    workstation_node=10, # Change delivery location
    weight_kg=100.0      # Change load weight
)
```

### Add More AGVs
Simply extend the setup loop:
```python
for i in range(1, 6):  # Creates 5 AGVs instead of 3
    Agv.objects.create(...)
```

---

## 🐛 Troubleshooting

### Issue: "No path found"
**Cause:** Node numbers don't exist in map
**Solution:** Check available nodes:
```python
from agv_data.models import ResourceAgent
nodes = ResourceAgent.objects.all().values_list('node_number', 'node_name')
print(list(nodes))
```

### Issue: "AGV has no valid start location"
**Cause:** `current_node` is None
**Solution:** Scripts automatically set valid `current_node`

### Issue: All bids are inf
**Cause:** Reservation table not accessible or all paths blocked
**Solution:** Check reservation table service is running

---

## 📝 Notes

1. **Scripts are idempotent:** Safe to run multiple times (deletes old data first)
2. **Order IDs:** Each test uses different order IDs (101, 102, 201-203) to avoid conflicts
3. **AGV IDs:** All tests use AGV IDs 1, 2, 3 (cleaned before each test)
4. **Timing:** Tests run sequentially, not in parallel

---

## 🎯 Quick Test Command

Run all 3 tests in sequence:
```powershell
docker compose exec server python sample-data/sample_test_1_idle_agvs.py; `
docker compose exec server python sample-data/sample_test_2_mixed_agvs.py; `
docker compose exec server python sample-data/sample_test_3_multiple_orders.py
```

---

## 📚 Related Documentation

- **Main Test Suite:** `agv_server/test_auction_system.py`
- **Auction Docs:** `docs/auction-logic/`
- **Quick Start:** `docs/auction-logic/auction-bidding-quickstart.md`
- **Integration:** `docs/auction-logic/INTEGRATION_VERIFICATION.md`

---

**Last Updated:** November 9, 2025
**Status:** ✅ All sample scripts tested and working
