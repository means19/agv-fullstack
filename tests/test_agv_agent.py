"""
Test AGV Agent Logic (Exploring Ant - DMAS-ET)

This script tests the DMAS_ET function with various route plans and scenarios.

Prerequisites:
- Django server running on localhost:8000
- Sample ResourceAgent data loaded (use create_sample_resources.py)

Run: python test_agv_agent.py
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agv_server'))

from agv_data.agv_agent import RouteStep, DMAS_ET, _calculate_energy_travel, _calculate_energy_wait
from agv_data.agv_agent_constants import K_ENERGY, K_TARDINESS, C_BASE, C_LOAD_COEFF, P_IDLE


def test_energy_calculations():
    """Test energy calculation helper functions"""
    print("\n" + "="*60)
    print("TEST 1: Energy Calculation Functions")
    print("="*60)
    
    # Test travel energy
    distance = 50.0  # meters
    load = 100.0     # kg
    expected = (C_BASE + C_LOAD_COEFF * load) * distance
    actual = _calculate_energy_travel(distance, load)
    
    print(f"\nTravel Energy Test:")
    print(f"  Distance: {distance}m")
    print(f"  Load: {load}kg")
    print(f"  Expected: {expected} kJ")
    print(f"  Actual: {actual} kJ")
    print(f"  [PASS]" if abs(expected - actual) < 0.001 else f"  [FAIL]")
    
    # Test wait energy
    delay = 60.0  # seconds
    expected = P_IDLE * delay / 1000.0
    actual = _calculate_energy_wait(delay)
    
    print(f"\nWait Energy Test:")
    print(f"  Delay: {delay}s")
    print(f"  Expected: {expected} kJ")
    print(f"  Actual: {actual} kJ")
    print(f"  [PASS]" if abs(expected - actual) < 0.001 else f"  [FAIL]")


def test_simple_route():
    """Test DMAS_ET with a simple route (no conflicts, no tardiness)"""
    print("\n" + "="*60)
    print("TEST 2: Simple Route (No Conflicts)")
    print("="*60)
    
    # Create route: Resource 1 -> Resource 2 -> Resource 3
    # All resources should be available immediately
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    
    route_plan = [
        RouteStep(
            resource_id=1,
            distance_m=50.0,
            duration_sec=30.0,
            load_kg=100.0,
            is_task_endpoint=False
        ),
        RouteStep(
            resource_id=2,
            distance_m=75.0,
            duration_sec=45.0,
            load_kg=100.0,
            is_task_endpoint=False
        ),
        RouteStep(
            resource_id=3,
            distance_m=100.0,
            duration_sec=60.0,
            load_kg=100.0,
            is_task_endpoint=False
        )
    ]
    
    cost = DMAS_ET(route_plan, start_time, agv_id="TEST_AGV_1")
    
    # Calculate expected cost (no delays, no tardiness)
    expected_energy = (
        _calculate_energy_travel(50.0, 100.0) +
        _calculate_energy_travel(75.0, 100.0) +
        _calculate_energy_travel(100.0, 100.0)
    )
    expected_cost = K_ENERGY * expected_energy + K_TARDINESS * 0
    
    print(f"\nExpected Cost: {expected_cost:.6f}")
    print(f"Actual Cost: {cost:.6f}")
    print(f"Difference: {abs(expected_cost - cost):.6f}")
    
    if cost != float('inf'):
        print("[PASS] - Route completed successfully")
    else:
        print("[FAIL] - Route returned inf")


def test_route_with_tardiness():
    """Test DMAS_ET with route that has task endpoints and due dates"""
    print("\n" + "="*60)
    print("TEST 3: Route with Task Endpoints and Tardiness")
    print("="*60)
    
    # Create route with tight deadlines
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)
    
    # First task due in 1 minute (should be on time)
    due_1 = start_time + timedelta(minutes=1)
    
    # Second task due in 2 minutes (might be late depending on delays)
    due_2 = start_time + timedelta(minutes=2)
    
    route_plan = [
        RouteStep(
            resource_id=1,
            distance_m=50.0,
            duration_sec=30.0,
            load_kg=50.0,
            is_task_endpoint=True,
            due_date=due_1
        ),
        RouteStep(
            resource_id=2,
            distance_m=100.0,
            duration_sec=60.0,
            load_kg=150.0,
            is_task_endpoint=True,
            due_date=due_2
        )
    ]
    
    cost = DMAS_ET(route_plan, start_time, agv_id="TEST_AGV_2")
    
    if cost != float('inf'):
        print("[PASS] - Route completed")
    else:
        print("[FAIL] - Route returned inf")


def test_varying_loads():
    """Test DMAS_ET with varying loads (pickup and dropoff)"""
    print("\n" + "="*60)
    print("TEST 4: Route with Varying Loads")
    print("="*60)
    
    start_time = datetime.now(timezone.utc) + timedelta(hours=3)
    
    route_plan = [
        # Empty AGV to warehouse
        RouteStep(
            resource_id=1,
            distance_m=100.0,
            duration_sec=60.0,
            load_kg=0.0,  # Empty
            is_task_endpoint=False
        ),
        # Pick up item (200kg)
        RouteStep(
            resource_id=2,
            distance_m=10.0,
            duration_sec=30.0,
            load_kg=200.0,  # Loaded
            is_task_endpoint=True,
            due_date=start_time + timedelta(minutes=5)
        ),
        # Travel to destination
        RouteStep(
            resource_id=3,
            distance_m=150.0,
            duration_sec=90.0,
            load_kg=200.0,  # Still loaded
            is_task_endpoint=False
        ),
        # Drop off
        RouteStep(
            resource_id=4,
            distance_m=10.0,
            duration_sec=30.0,
            load_kg=0.0,  # Empty again
            is_task_endpoint=True,
            due_date=start_time + timedelta(minutes=10)
        )
    ]
    
    cost = DMAS_ET(route_plan, start_time, agv_id="TEST_AGV_3")
    
    if cost != float('inf'):
        print("[PASS] - Route with varying loads completed")
    else:
        print("[FAIL] - Route returned inf")


def test_invalid_route():
    """Test DMAS_ET with invalid route (empty, invalid resource)"""
    print("\n" + "="*60)
    print("TEST 5: Invalid Routes")
    print("="*60)
    
    # Test empty route
    print("\nTest 5.1: Empty route")
    start_time = datetime.now(timezone.utc)
    cost = DMAS_ET([], start_time, agv_id="TEST_EMPTY")
    
    if cost == float('inf'):
        print("[PASS] - Empty route returns inf")
    else:
        print("[FAIL] - Empty route should return inf")
    
    # Test invalid resource ID (assuming resource 999999 doesn't exist)
    print("\nTest 5.2: Invalid resource ID")
    route_plan = [
        RouteStep(
            resource_id=999999,
            distance_m=50.0,
            duration_sec=30.0,
            load_kg=100.0,
            is_task_endpoint=False
        )
    ]
    
    cost = DMAS_ET(route_plan, start_time, agv_id="TEST_INVALID")
    
    if cost == float('inf'):
        print("[PASS] - Invalid resource returns inf")
    else:
        print("[FAIL] - Invalid resource should return inf")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AGV AGENT (DMAS-ET) TEST SUITE")
    print("="*60)
    print(f"\nTest started at: {datetime.now()}")
    print("\nConfiguration:")
    print(f"  K_ENERGY = {K_ENERGY}")
    print(f"  K_TARDINESS = {K_TARDINESS}")
    print(f"  C_BASE = {C_BASE} kJ/m")
    print(f"  C_LOAD_COEFF = {C_LOAD_COEFF} kJ/(kg·m)")
    print(f"  P_IDLE = {P_IDLE} W")
    
    try:
        # Run all tests
        test_energy_calculations()
        test_simple_route()
        test_route_with_tardiness()
        test_varying_loads()
        test_invalid_route()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("\nNote: Some tests may show delays or conflicts depending on")
        print("the current state of the Reservation Table. This is expected.")
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
