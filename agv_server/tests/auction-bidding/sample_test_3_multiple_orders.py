#!/usr/bin/env python
"""
Sample Script 3: Test Multiple Orders Sequentially
Scenario: Test auction với nhiều orders khác nhau
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
print("SAMPLE TEST 3: MULTIPLE ORDERS SEQUENTIAL AUCTION")
print("=" * 70)

# Step 1: Setup AGVs
print("\n[STEP 1] Setting up 3 idle AGVs...")
Agv.objects.filter(agv_id__in=[1, 2, 3]).delete()

for i, node in enumerate([2, 8, 6], start=1):
    Agv.objects.create(
        agv_id=i,
        preferred_parking_node=1,
        motion_state=Agv.IDLE,
        current_node=node,
        remaining_path=[],
        journey_phase=Agv.OUTBOUND
    )
    print(f"  ✓ AGV {i}: IDLE at CA-{node:02d}")

# Step 2: Create Multiple Orders
print("\n[STEP 2] Creating 3 different orders...")
Order.objects.filter(order_id__in=[201, 202, 203]).delete()

orders_data = [
    {"id": 201, "parking": 1, "storage": 5, "workstation": 10, "desc": "Near orders"},
    {"id": 202, "parking": 1, "storage": 15, "workstation": 20, "desc": "Far orders"},
    {"id": 203, "parking": 1, "storage": 3, "workstation": 7, "desc": "Short distance"},
]

orders = []
for data in orders_data:
    order = Order.objects.create(
        order_id=data["id"],
        order_date=date.today(),
        start_time=time(9 + len(orders), 0),
        parking_node=data["parking"],
        storage_node=data["storage"],
        workstation_node=data["workstation"]
    )
    orders.append(order)
    print(f"  ✓ Order {order.order_id}: {data['desc']} (storage={data['storage']}, workstation={data['workstation']})")

print(f"      Note: All orders using default load weight (100 kg) from bidding service")

# Step 3: Run Auctions
print("\n[STEP 3] Running auctions for each order...")
results = []

for idx, order in enumerate(orders, start=1):
    print("\n" + "-" * 70)
    print(f"AUCTION {idx}/3 - Order {order.order_id}")
    print("-" * 70)
    print(f"Storage: CA-{order.storage_node:02d}, Workstation: CA-{order.workstation_node:02d}")
    
    result = task_manager.run_auction(order)
    
    if result:
        winner_id, winning_bid = result
        results.append({
            "order_id": order.order_id,
            "winner": winner_id,
            "bid": winning_bid,
            "storage": order.storage_node,
            "workstation": order.workstation_node
        })
        print(f"  🏆 Winner: AGV {winner_id}, Bid: {winning_bid:.6f}")
    else:
        print("  ❌ No winner")
        results.append({
            "order_id": order.order_id,
            "winner": None,
            "bid": None,
            "storage": order.storage_node,
            "workstation": order.workstation_node
        })

# Summary
print("\n" + "=" * 70)
print("AUCTION RESULTS SUMMARY")
print("=" * 70)
print(f"{'Order':<10} {'Storage':<10} {'Workstation':<12} {'Winner':<10} {'Bid':<15}")
print("-" * 70)

for r in results:
    winner_str = f"AGV {r['winner']}" if r['winner'] else "None"
    bid_str = f"{r['bid']:.6f}" if r['bid'] else "N/A"
    print(f"{r['order_id']:<10} CA-{r['storage']:02d}{'':<5} CA-{r['workstation']:02d}{'':<7} {winner_str:<10} {bid_str:<15}")

print("=" * 70)

winners_count = sum(1 for r in results if r['winner'] is not None)
print(f"\n✅ SAMPLE TEST 3 COMPLETED: {winners_count}/{len(results)} auctions successful")
print("=" * 70)
