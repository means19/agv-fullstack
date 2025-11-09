#!/usr/bin/env python
"""
Sample Script 1: Test với 3 IDLE AGVs
Scenario: Tất cả AGVs đều rảnh, test bidding từ các vị trí khác nhau
"""

import os
import sys
import django


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agv_server.settings')
django.setup()

from agv_data.models import Agv
from order_data.models import Order
from agv_services import task_manager
from datetime import date, time

print("=" * 70)
print("SAMPLE TEST 1: AUCTION WITH 3 IDLE AGVs")
print("=" * 70)

# Step 1: Setup AGVs
print("\n[STEP 1] Setting up 3 idle AGVs at different locations...")
Agv.objects.filter(agv_id__in=[1, 2, 3]).delete()

agvs_setup = [
    {"agv_id": 1, "node": 2, "name": "CA-02"},
    {"agv_id": 2, "node": 8, "name": "CA-08"},
    {"agv_id": 3, "node": 6, "name": "CA-06"},
]

for setup in agvs_setup:
    Agv.objects.create(
        agv_id=setup["agv_id"],
        preferred_parking_node=1,
        motion_state=Agv.IDLE,
        current_node=setup["node"],
        remaining_path=[],
        journey_phase=Agv.OUTBOUND
    )
    print(f"  ✓ AGV {setup['agv_id']}: IDLE at {setup['name']}")

# Step 2: Create Order
print("\n[STEP 2] Creating test order...")
Order.objects.filter(order_id=101).delete()
order = Order.objects.create(
    order_id=101,
    order_date=date.today(),
    start_time=time(9, 0),
    parking_node=1,
    storage_node=5,
    workstation_node=10
)
print(f"  ✓ Order {order.order_id}: parking={order.parking_node}, storage={order.storage_node}, workstation={order.workstation_node}")
print(f"      Note: Using default load weight (100 kg) from bidding service")

# Step 3: Run Auction
print("\n[STEP 3] Running auction...")
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
    print(f"   Winning Bid: {winning_bid:.6f}")
    print(f"   State: {winner.get_motion_state_display()}")
    print("=" * 70)
    
    print("\n✅ SAMPLE TEST 1 COMPLETED SUCCESSFULLY!")
else:
    print("\n❌ AUCTION FAILED - No winner selected")

print("\n" + "=" * 70)
