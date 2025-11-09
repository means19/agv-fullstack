#!/usr/bin/env python
"""
Sample Script 2: Test với MIXED AGVs (2 idle + 1 busy)
Scenario: Test busy AGV bidding với J1 calculation
"""

import os
import sys
import django

# Add agv_server to path (go up 2 levels from tests/auction-bidding/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agv_server.settings')
django.setup()

from agv_data.models import Agv
from order_data.models import Order
from agv_services import task_manager
from datetime import date, time

print("=" * 70)
print("SAMPLE TEST 2: AUCTION WITH MIXED AGVs (2 IDLE + 1 BUSY)")
print("=" * 70)

# Step 1: Setup AGVs
print("\n[STEP 1] Setting up 3 AGVs (2 idle + 1 busy)...")
Agv.objects.filter(agv_id__in=[1, 2, 3]).delete()

# Create dummy order for busy AGV
Order.objects.filter(order_id=999).delete()
dummy_order = Order.objects.create(
    order_id=999,
    order_date=date.today(),
    start_time=time(8, 0),
    parking_node=1,
    storage_node=3,
    workstation_node=11
)

# AGV 1: IDLE
Agv.objects.create(
    agv_id=1,
    preferred_parking_node=1,
    motion_state=Agv.IDLE,
    current_node=2,
    remaining_path=[],
    journey_phase=Agv.OUTBOUND
)
print("  ✓ AGV 1: IDLE at CA-02")

# AGV 2: BUSY (completing task from node 8 to 11)
Agv.objects.create(
    agv_id=2,
    preferred_parking_node=1,
    motion_state=Agv.MOVING,
    current_node=8,
    remaining_path=[9, 10, 11],  # Just node numbers, not dicts
    journey_phase=Agv.INBOUND,  # Loaded, returning
    active_order_id=999
)
print("  ✓ AGV 2: BUSY (MOVING) at CA-08, completing to CA-11")
print("           Remaining path: CA-08 → CA-09 → CA-10 → CA-11")

# AGV 3: IDLE
Agv.objects.create(
    agv_id=3,
    preferred_parking_node=1,
    motion_state=Agv.IDLE,
    current_node=6,
    remaining_path=[],
    journey_phase=Agv.OUTBOUND
)
print("  ✓ AGV 3: IDLE at CA-06")

# Step 2: Create Order
print("\n[STEP 2] Creating test order...")
Order.objects.filter(order_id=102).delete()
order = Order.objects.create(
    order_id=102,
    order_date=date.today(),
    start_time=time(10, 0),
    parking_node=1,
    storage_node=5,
    workstation_node=10
)
print(f"  ✓ Order {order.order_id}: parking={order.parking_node}, storage={order.storage_node}, workstation={order.workstation_node}")
print(f"      Note: Using default load weight (100 kg) from bidding service")

# Step 3: Run Auction
print("\n[STEP 3] Running auction with mixed AGVs...")
print("  Note: Busy AGV will calculate J1 from remaining_path")
print("-" * 70)

result = task_manager.run_auction(order)

print("-" * 70)

if result:
    winner_id, winning_bid = result
    winner = Agv.objects.get(agv_id=winner_id)
    
    print("\n" + "=" * 70)
    print("AUCTION RESULT")
    print("=" * 70)
    print(f"🏆 Winner: AGV {winner_id}")
    print(f"   Current Position: CA-{winner.current_node:02d}")
    print(f"   State: {winner.get_motion_state_display()}")
    if winner.motion_state == Agv.MOVING:
        print(f"   Completion Node: CA-{winner.remaining_path[-1]['to_node']:02d}")
        print(f"   Note: Bid calculated from completion position (marginal cost)")
    print(f"   Winning Bid: {winning_bid:.6f}")
    print("=" * 70)
    
    print("\n✅ SAMPLE TEST 2 COMPLETED SUCCESSFULLY!")
    print("\nKey Insight:")
    if winner.motion_state == Agv.MOVING:
        print("  → Busy AGV won! This shows marginal cost calculation working.")
        print("  → J1 (current task) was subtracted, showing only new task cost.")
    else:
        print("  → Idle AGV won! Busy AGV's current task made it less competitive.")
else:
    print("\n❌ AUCTION FAILED - No winner selected")

print("\n" + "=" * 70)
