"""
Test Script for SSI-DMAS-ET Auction System

This script tests the complete auction workflow:
1. Auctioneer calculates baseline
2. AGVs submit bids
3. Winner is selected
4. Task is assigned

Run this after:
- Django server is running
- Map data is loaded (ResourceAgent nodes/edges)
- At least one AGV exists
- At least one Order exists
"""

import os
import sys
import django

# Setup Django environment (go up 2 levels from tests/auction-bidding/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agv_server.settings')
django.setup()

from agv_services.task_manager import task_manager
from order_data.models import Order
from agv_data.models import Agv, ResourceAgent
from agv_services.auctioneer_service import auctioneer_service
from agv_services.bidding_service import BiddingService


def test_auctioneer_service():
    """Test baseline calculation"""
    print("\n" + "="*80)
    print("TEST 1: AUCTIONEER SERVICE - BASELINE CALCULATION")
    print("="*80)
    
    try:
        order = Order.objects.first()
        if not order:
            print("[ERROR] No orders found in database")
            return False
        
        print(f"Testing with Order {order.order_id}")
        
        E_baseline, TFT_baseline = auctioneer_service.calculate_baseline(order)
        
        if E_baseline == float('inf'):
            print("[FAIL] Baseline calculation returned inf")
            return False
        
        print(f"\n[SUCCESS] Baseline calculated:")
        print(f"  E_baseline = {E_baseline:.4f} kJ")
        print(f"  TFT_baseline = {TFT_baseline:.2f} sec")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bidding_service():
    """Test bid calculation for a single AGV"""
    print("\n" + "="*80)
    print("TEST 2: BIDDING SERVICE - BID CALCULATION")
    print("="*80)
    
    try:
        order = Order.objects.first()
        if not order:
            print("[ERROR] No orders found")
            return False
        
        agv = Agv.objects.filter(motion_state=Agv.IDLE).first()
        if not agv:
            print("[ERROR] No idle AGVs found")
            return False
        
        print(f"Testing with Order {order.order_id} and AGV {agv.agv_id}")
        
        # Calculate baseline first
        E_baseline, TFT_baseline = auctioneer_service.calculate_baseline(order)
        
        if E_baseline == float('inf'):
            print("[FAIL] Cannot calculate baseline")
            return False
        
        # Calculate bid
        bidding_service = BiddingService()
        bid = bidding_service.calculate_bid_for_agv(
            agv=agv,
            order=order,
            E_baseline=E_baseline,
            TFT_baseline=TFT_baseline
        )
        
        if bid == float('inf'):
            print("[FAIL] Bid calculation returned inf")
            return False
        
        print(f"\n[SUCCESS] Bid calculated:")
        print(f"  AGV {agv.agv_id} bid = {bid:.6f}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auction_process():
    """Test complete auction process"""
    print("\n" + "="*80)
    print("TEST 3: COMPLETE AUCTION PROCESS")
    print("="*80)
    
    try:
        order = Order.objects.first()
        if not order:
            print("[ERROR] No orders found")
            return False
        
        idle_agvs = Agv.objects.filter(motion_state=Agv.IDLE)
        if idle_agvs.count() == 0:
            print("[ERROR] No idle AGVs found")
            return False
        
        print(f"Testing with Order {order.order_id}")
        print(f"Available AGVs: {idle_agvs.count()}")
        
        # Run auction
        result = task_manager.run_auction(order)
        
        if result is None:
            print("[FAIL] Auction returned None")
            return False
        
        winner_id, winning_bid = result
        
        print(f"\n[SUCCESS] Auction completed:")
        print(f"  Winner: AGV {winner_id}")
        print(f"  Winning bid: {winning_bid:.6f}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("\n" + "="*80)
    print("CHECKING PREREQUISITES")
    print("="*80)
    
    errors = []
    
    # Check for ResourceAgent nodes
    nodes_count = ResourceAgent.objects.filter(
        resource_type__in=['CA', 'DEPOT', 'STATION']
    ).count()
    print(f"✓ ResourceAgent nodes: {nodes_count}")
    if nodes_count == 0:
        errors.append("No ResourceAgent nodes found. Please import map data.")
    
    # Check for ResourceAgent edges
    edges_count = ResourceAgent.objects.filter(resource_type='LSA').count()
    print(f"✓ ResourceAgent edges: {edges_count}")
    if edges_count == 0:
        errors.append("No LSA edges found. Please import map data.")
    
    # Check for AGVs
    agvs_count = Agv.objects.count()
    idle_agvs_count = Agv.objects.filter(motion_state=Agv.IDLE).count()
    print(f"✓ Total AGVs: {agvs_count} (Idle: {idle_agvs_count})")
    if idle_agvs_count == 0:
        errors.append("No idle AGVs found. Please create idle AGVs for testing.")
    
    # Check for Orders
    orders_count = Order.objects.count()
    print(f"✓ Orders: {orders_count}")
    if orders_count == 0:
        errors.append("No orders found. Please create test orders.")
    
    if errors:
        print("\n[ERROR] Prerequisites not met:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("\n[SUCCESS] All prerequisites met!")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SSI-DMAS-ET AUCTION SYSTEM - TEST SUITE")
    print("="*80)
    print("\nThis test suite validates:")
    print("  1. Auctioneer baseline calculation (Algorithm A)")
    print("  2. AGV bid calculation (Algorithm B)")
    print("  3. Complete auction process with winner selection")
    print("\nRunning tests...")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n[ABORT] Cannot run tests without prerequisites")
        return
    
    # Run tests
    results = []
    
    results.append(("Auctioneer Service", test_auctioneer_service()))
    results.append(("Bidding Service", test_bidding_service()))
    results.append(("Auction Process", test_auction_process()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! Auction system is working correctly.")
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed. Please review errors above.")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
