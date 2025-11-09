# Reservation Table Tests

This directory contains test scripts for the Reservation Table system.

## Test Files

### 1. `test_reservation_table.py`
**Purpose**: Sequential functional testing of the Reservation Table system.

**What it tests:**
- List resources (CA/LSA)
- Query earliest available slot (Exploring Ant)
- Book a slot (Intention Ant)
- Conflict detection
- List bookings by AGV and resource
- Cancel bookings

**Run:**
```bash
cd ..
python tests/test_reservation_table.py
```

**Expected Result:** All 9 tests pass ✅

---

### 2. `test_concurrent_booking.py`
**Purpose**: Concurrent booking test to verify race condition handling.

**What it tests:**
- 10 threads simultaneously attempt to book the SAME time slot
- Verifies STRICT/FAIL-FAST approach (Approach 2)
- Ensures auction integrity for SSI-DMAS

**Run:**
```bash
cd ..
python tests/test_concurrent_booking.py
```

**Expected Result:**
- Exactly 1 booking succeeds (201) ✅
- Exactly 9 bookings fail with 409 Conflict ✅
- No overlapping bookings ✅

**This is the CRITICAL test** that validates the system is ready for production!

---

### 3. `check_overlaps.py`
**Purpose**: Utility script to check for overlapping bookings.

**What it does:**
- Fetches all bookings for a resource
- Checks for any time overlaps
- Reports if concurrent bookings are properly handled

**Run:**
```bash
cd ..
python tests/check_overlaps.py
```

**Expected Result:** "NO OVERLAPS FOUND" ✅

---

## Testing Workflow

### Initial Setup
```bash
# Make sure Docker is running
docker-compose up -d

# Run migrations
docker-compose exec server python manage.py makemigrations
docker-compose exec server python manage.py migrate

# Create sample resources
docker-compose exec server python create_sample_resources.py
```

### Run All Tests
```bash
# 1. Functional test
python tests/test_reservation_table.py

# 2. Concurrency test (THE MOST IMPORTANT)
python tests/test_concurrent_booking.py

# 3. Verify no overlaps
python tests/check_overlaps.py
```

---

## Test Results Interpretation

### ✅ Success Criteria

#### Functional Test (`test_reservation_table.py`)
- All 9 tests pass
- Query returns correct earliest slot
- Bookings are created successfully
- Conflicts are detected properly

#### Concurrency Test (`test_concurrent_booking.py`)
- **EXACTLY 1 booking succeeds** (Status 201)
- **EXACTLY 9 bookings fail** (Status 409)
- This validates:
  - Auction integrity is maintained
  - No race conditions
  - Proper transaction isolation
  - AGVs receive correct feedback (fail-fast)

#### Overlap Check (`check_overlaps.py`)
- **NO OVERLAPS FOUND**
- All bookings have distinct time windows
- No double-booking

---

## Why Concurrency Test is Critical

The concurrent test validates the **Strict/Fail-Fast (Approach 2)** implementation:

### ❌ Wrong Approach (Auto-Serialize)
10 AGVs all get bookings but at different times → Breaks auction integrity

### ✅ Correct Approach (Strict/Fail-Fast)  
- 1 AGV gets the exact slot it bid on
- 9 AGVs get 409 and must re-bid with new information
- Ensures AGVs run on accurate schedules

**This is essential for SSI-DMAS algorithm correctness!**

---

## Troubleshooting

### Server Connection Error
```bash
# Make sure server is running
docker-compose ps

# Restart if needed
docker-compose restart server
```

### Import Errors
```bash
# Install requests if needed
pip install requests
```

### All Tests Succeed in Concurrent Test (Wrong!)
If all 10 bookings succeed, the system is using auto-serialize (Approach 1) which breaks auction integrity. Check that `services.py::create_booking()` uses:
- `select_for_update()` on ResourceAgent
- `select_for_update()` on conflict check
- Strict exact-slot-only booking (no auto-finding next slot)

---

## Next Steps After Tests Pass

1. ✅ Reservation Table validated
2. 📝 Implement Sequential Single Item algorithm
3. 📝 Integrate Exploring Ant logic
4. 📝 Integrate Intention Ant logic  
5. 📝 Implement full D-MAS coordination
6. 📝 End-to-end multi-AGV testing
