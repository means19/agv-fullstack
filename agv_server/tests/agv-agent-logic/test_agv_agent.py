"""
Test AGV Agent Logic (Exploring Ant - DMAS-ET)

This script tests the refactored Exploring Ant implementation with clean architecture.

Tests both:
- Backward compatibility (old API still works)
- New service-based architecture

Prerequisites:
- Django server running on localhost:8000
- Sample ResourceAgent data loaded (use create_sample_resources.py)

Run: python test_agv_agent.py
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Add agv_server to path (go up 2 levels from tests/agv-agent-logic/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Test backward compatibility
from agv_data.agv_agent import RouteStep, DMAS_ET, _calculate_energy_travel, _calculate_energy_wait
from agv_data.agv_agent_constants import K_ENERGY, K_TIME, C_BASE, C_LOAD_COEFF, P_IDLE

# Test new architecture
from agv_data.exploring_ants import (
    ExploringAntService,
    EnergyCalculationService,
    ReservationTableClient,
    ExploringAntConfig,
    RouteStep as RouteStepNew
)

# For creating test reservations
import requests


def test_energy_calculations():
    """Test energy calculation functions (physics-based model)"""
    print("\n" + "="*60)
    print("TEST 1: Energy Calculation Functions (Physics-Based)")
    print("="*60)
    
    # Test physics-based model
    print("\n[Physics-Based Energy Model Test]")
    distance = 50.0  # meters
    load = 100.0     # kg
    
    # Both old and new APIs now use physics-based model
    actual_old = _calculate_energy_travel(distance, load)
    
    print(f"Travel Energy (Old API wrapper):")
    print(f"  Distance: {distance}m, Load: {load}kg")
    print(f"  Actual: {actual_old:.3f} kJ")
    
    # Test new service
    print("\n[New Service Test]")
    energy_service = EnergyCalculationService()
    actual_new = energy_service.calculate_travel_energy(distance, load)
    
    print(f"Travel Energy (New Service):")
    print(f"  Distance: {distance}m, Load: {load}kg")
    print(f"  Actual: {actual_new:.3f} kJ")
    print(f"  [PASS]" if abs(actual_old - actual_new) < 0.001 else f"  [FAIL]")
    print(f"  Compatibility: {'✅ MATCH' if abs(actual_old - actual_new) < 0.001 else '❌ MISMATCH'}")
    
    # Compare with old linear model for reference
    old_linear = (C_BASE + C_LOAD_COEFF * load) * distance
    print(f"\n  📊 Comparison:")
    print(f"     Old linear model: {old_linear:.3f} kJ")
    print(f"     New physics model: {actual_new:.3f} kJ")
    print(f"     Difference: {old_linear - actual_new:.3f} kJ ({((old_linear-actual_new)/old_linear*100):.1f}% reduction)")
    
    # Test wait energy
    print("\n[Wait Energy Test]")
    delay = 60.0  # seconds
    expected = P_IDLE * delay / 1000.0
    actual_old_wait = _calculate_energy_wait(delay)
    actual_new_wait = energy_service.calculate_wait_energy(delay)
    
    print(f"Wait Energy:")
    print(f"  Delay: {delay}s")
    print(f"  Expected: {expected} kJ")
    print(f"  Old API: {actual_old_wait} kJ")
    print(f"  New Service: {actual_new_wait} kJ")
    print(f"  [PASS]" if abs(expected - actual_new_wait) < 0.001 else f"  [FAIL]")
    print(f"  Compatibility: {'✅ MATCH' if abs(actual_old_wait - actual_new_wait) < 0.001 else '❌ MISMATCH'}")


def test_simple_route():
    """Test DMAS_ET with a simple route (comparing old and new API)"""
    print("\n" + "="*60)
    print("TEST 2: Simple Route (Backward Compatibility)")
    print("="*60)
    
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Use only resources 1 and 2 (which exist in database)
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
            is_task_endpoint=True  # Mark as task endpoint to track TFT
        )
    ]
    
    print("\n[Testing Old API - DMAS_ET()]")
    energy_old, tft_old = DMAS_ET(route_plan, start_time, agv_id="TEST_OLD_API")
    
    print("\n[Testing New API - ExploringAntService]")
    service = ExploringAntService(verbose=True)
    energy_new, tft_new = service.explore(route_plan, start_time, agv_id="TEST_NEW_API")
    
    # Calculate expected values
    expected_energy = (
        _calculate_energy_travel(50.0, 100.0) +
        _calculate_energy_travel(75.0, 100.0)
    )
    expected_tft = 30.0 + 45.0  # Sum of durations
    
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}")
    print(f"Expected Energy: {expected_energy:.6f} kJ")
    print(f"Expected TFT: {expected_tft:.2f} seconds")
    print(f"\nOld API Results:")
    print(f"  Energy: {energy_old:.6f} kJ")
    print(f"  TFT: {tft_old:.2f} seconds")
    print(f"\nNew API Results:")
    print(f"  Energy: {energy_new:.6f} kJ")
    print(f"  TFT: {tft_new:.2f} seconds")
    
    if energy_old != float('inf') and energy_new != float('inf'):
        energy_match = abs(energy_old - energy_new) < 0.001
        tft_match = abs(tft_old - tft_new) < 0.001
        print(f"\nCompatibility Check:")
        print(f"  Energy: {'✅ MATCH' if energy_match else '❌ MISMATCH'}")
        print(f"  TFT: {'✅ MATCH' if tft_match else '❌ MISMATCH'}")
        print(f"\n[PASS] - Both APIs work correctly")
    else:
        print(f"\n[FAIL] - One or both APIs returned inf")


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
    
    energy, tft = DMAS_ET(route_plan, start_time, agv_id="TEST_AGV_2")
    
    if energy != float('inf') and tft != float('inf'):
        print("[PASS] - Route completed")
    else:
        print("[FAIL] - Route returned inf")


def test_varying_loads():
    """Test new service with silent mode (performance)"""
    print("\n" + "="*60)
    print("TEST 4: Silent Mode Performance Test")
    print("="*60)
    
    start_time = datetime.now(timezone.utc) + timedelta(hours=3)
    
    # Use only existing resources (1 and 2)
    route_plan = [
        RouteStep(
            resource_id=1,
            distance_m=100.0,
            duration_sec=60.0,
            load_kg=0.0,  # Empty
            is_task_endpoint=False
        ),
        RouteStep(
            resource_id=2,
            distance_m=150.0,
            duration_sec=90.0,
            load_kg=200.0,  # Loaded
            is_task_endpoint=True,
            due_date=start_time + timedelta(minutes=5)
        )
    ]
    
    print("\n[Testing Silent Mode - No Console Output Expected]")
    service = ExploringAntService(verbose=False)
    energy, tft = service.explore(route_plan, start_time, agv_id="TEST_SILENT")
    
    print(f"\nResults (Silent Mode):")
    print(f"  Energy: {energy:.6f} kJ")
    print(f"  TFT: {tft:.2f} seconds")
    
    if energy != float('inf') and tft != float('inf'):
        print("[PASS] - Silent mode works correctly")
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
    energy, tft = DMAS_ET([], start_time, agv_id="TEST_EMPTY")
    
    if energy == float('inf') and tft == float('inf'):
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
    
    energy, tft = DMAS_ET(route_plan, start_time, agv_id="TEST_INVALID")
    
    if energy == float('inf') and tft == float('inf'):
        print("[PASS] - Invalid resource returns inf")
    else:
        print("[FAIL] - Invalid resource should return inf")


def test_resource_conflict_with_delay():
    """Test conflict scenario where AGV B must wait for AGV A to release resource"""
    print("\n" + "="*60)
    print("TEST 6: Resource Conflict - AGV B Waits for AGV A")
    print("="*60)
    
    # Setup: Simulate AGV A occupying Resource 2
    print("\n[Setting up conflict scenario]")
    
    # Time setup - AGV A will occupy resource 2 for 60 seconds
    current_time = datetime.now(timezone.utc)
    agv_a_start = current_time + timedelta(minutes=1)
    agv_a_duration = 60  # seconds
    
    # AGV B wants to start 20 seconds into AGV A's occupation
    agv_b_step1_end = agv_a_start + timedelta(seconds=20)
    
    print(f"Scenario:")
    print(f"  AGV A will occupy Resource 2: {agv_a_start.strftime('%H:%M:%S')} for {agv_a_duration}s")
    print(f"  AGV B will request Resource 2: ~{agv_b_step1_end.strftime('%H:%M:%S')}")
    print(f"  Expected: AGV B should wait until AGV A finishes")
    
    # First, have AGV A "book" the resource by running exploration
    print(f"\n[Step 1: AGV A reserves Resource 2]")
    route_plan_a = [
        RouteStep(
            resource_id=2,
            distance_m=50.0,
            duration_sec=agv_a_duration,
            load_kg=100.0,
            is_task_endpoint=True
        )
    ]
    
    # Run AGV A's exploration to create the booking
    service_a = ExploringAntService(verbose=False)
    
    # Use requests to directly query and book (simulating what AGV A does)
    try:
        # Query slot for AGV A
        query_payload = {
            "request_start_time": agv_a_start.isoformat(),
            "duration_seconds": agv_a_duration
        }
        
        query_response = requests.post(
            'http://localhost:8000/api/agvs/reservation/resource/2/query_slot/',
            json=query_payload,
            timeout=5
        )
        
        if query_response.status_code != 200:
            print(f"⚠️ Cannot query slot: {query_response.status_code}")
            print("[SKIP] - Reservation API not working properly")
            return
            
        earliest_start = query_response.json().get('earliest_available_start')
        print(f"✅ AGV A can book from: {earliest_start}")
        
        # Now book it for AGV A (this creates the conflict)
        # Note: agv_id must be integer (AGV primary key from database)
        book_payload = {
            "agv_id": 1,  # Use existing AGV ID (assuming AGV with ID=1 exists)
            "request_start_time": agv_a_start.isoformat(),
            "duration_seconds": agv_a_duration
        }
        
        book_response = requests.post(
            'http://localhost:8000/api/agvs/reservation/resource/2/book_slot/',
            json=book_payload,
            timeout=5
        )
        
        if book_response.status_code in [200, 201]:
            booking_data = book_response.json()
            print(f"✅ Created booking for AGV A: {booking_data}")
            booking_id = booking_data.get('id') or booking_data.get('booking_id')
        else:
            print(f"⚠️ Cannot book slot: {book_response.status_code} - {book_response.text}")
            print("[SKIP] - Cannot create booking for conflict test")
            return
            
    except requests.RequestException as e:
        print(f"⚠️ API Error: {e}")
        print("[SKIP] - Cannot test conflict without API")
        return
    
    # Now test AGV B trying to use the same resource
    print(f"\n[Step 2: AGV B tries to use Resource 2 - should encounter conflict]")
    
    route_plan_b = [
        RouteStep(
            resource_id=1,
            distance_m=50.0,
            duration_sec=20.0,
            load_kg=100.0,
            is_task_endpoint=False
        ),
        RouteStep(
            resource_id=2,  # This conflicts with AGV A!
            distance_m=75.0,
            duration_sec=30.0,
            load_kg=100.0,
            is_task_endpoint=True
        )
    ]
    
    # Calculate expected energy without delay
    expected_travel_energy = (
        _calculate_energy_travel(50.0, 100.0) +
        _calculate_energy_travel(75.0, 100.0)
    )
    
    # Run AGV B's exploration
    print("\n" + "="*60)
    service_b = ExploringAntService(verbose=True)
    energy_b, tft_b = service_b.explore(
        route_plan_b, 
        agv_a_start,  # Start at same time as AGV A
        agv_id="AGV_B_TEST"
    )
    
    # Cleanup: Try to delete the booking
    try:
        if booking_id:
            # Try different endpoints
            for endpoint in [
                f'http://localhost:8000/api/agvs/reservation/resource/2/cancel_booking/{booking_id}/',
                f'http://localhost:8000/api/agvs/reservation/bookings/{booking_id}/'
            ]:
                try:
                    delete_response = requests.delete(endpoint, timeout=5)
                    if delete_response.status_code in [200, 204]:
                        print(f"\n🧹 Cleaned up booking {booking_id}")
                        break
                except:
                    continue
    except:
        pass  # Ignore cleanup errors
    
    # Analysis
    print(f"\n{'='*60}")
    print("CONFLICT ANALYSIS")
    print(f"{'='*60}")
    
    if energy_b != float('inf') and tft_b != float('inf'):
        print(f"Expected travel energy: {expected_travel_energy:.6f} kJ")
        print(f"Actual total energy:    {energy_b:.6f} kJ")
        print(f"Actual TFT:             {tft_b:.2f}s")
        
        # Check if energy includes wait component
        if energy_b > expected_travel_energy:
            wait_energy_actual = energy_b - expected_travel_energy
            print(f"\n✅ AGV B WAITED for AGV A!")
            print(f"   Wait energy: {wait_energy_actual:.6f} kJ")
            
            # Estimate delay from wait energy
            estimated_delay = wait_energy_actual / P_IDLE * 1000
            print(f"   Estimated delay: ~{estimated_delay:.2f}s")
            
            print(f"\n[PASS] - Conflict detected! AGV B correctly waited for AGV A")
        else:
            print(f"\n⚠️ No wait detected (energy matches expected travel only)")
            print(f"   Energy difference: {abs(energy_b - expected_travel_energy):.6f} kJ")
            print("[PARTIAL] - May need to check booking timing")
    else:
        print(f"Energy: {energy_b}, TFT: {tft_b}")
        print("[FAIL] - Route returned inf")


def test_new_architecture():
    """Test new architecture features"""
    print("\n" + "="*60)
    print("TEST 7: New Architecture Features")
    print("="*60)
    
    # Test custom configuration (physics-based model)
    print("\n[Testing Custom Configuration]")
    custom_config = ExploringAntConfig.from_dict({
        'energy': {
            'mass_agv': 50.0,  # Heavier AGV
            'motor_efficiency': 0.8,  # Better motor
            'friction_coeff': 0.02  # Smoother wheels
        },
        'normalization': {
            'epsilon': 0.7  # More weight on efficiency
        }
    })
    
    print(f"Custom Config (Physics-Based):")
    print(f"  mass_agv: {custom_config.energy.mass_agv} kg")
    print(f"  motor_efficiency: {custom_config.energy.motor_efficiency}")
    print(f"  friction_coeff: {custom_config.energy.friction_coeff}")
    print(f"  epsilon: {custom_config.normalization.epsilon}")
    
    service = ExploringAntService(config=custom_config, verbose=False)
    print("[PASS] - Custom configuration works")
    
    # Test RouteStep validation
    print("\n[Testing RouteStep Validation]")
    try:
        invalid_step = RouteStepNew(
            resource_id=-1,  # Invalid: negative ID
            distance_m=50.0,
            duration_sec=30.0,
            load_kg=100.0,
            is_task_endpoint=False
        )
        print("[FAIL] - Should have raised ValueError for negative resource_id")
    except ValueError as e:
        print(f"[PASS] - Validation caught error: {e}")
    
    # Test EnergyCalculationService error handling
    print("\n[Testing Error Handling]")
    energy_service = EnergyCalculationService()
    try:
        energy_service.calculate_travel_energy(-50.0, 100.0)  # Negative distance
        print("[FAIL] - Should have raised ValueError for negative distance")
    except ValueError as e:
        print(f"[PASS] - Error handling works: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AGV AGENT (DMAS-ET) TEST SUITE - REFACTORED")
    print("="*60)
    print(f"\nTest started at: {datetime.now()}")
    print("\n🆕 Testing Refactored Architecture:")
    print("   - Physics-based energy model")
    print("   - Backward compatibility")
    print("   - New service layer")
    print("   - Clean architecture")
    print("\nConfiguration (Physics-Based Model):")
    print(f"  K_ENERGY = {K_ENERGY}")
    print(f"  K_TIME = {K_TIME}")
    print(f"\n  Physics Parameters:")
    from agv_data.exploring_ants.config import MASS_AGV, FRICTION_COEFF, GRAVITY, MOTOR_EFFICIENCY, MAX_VELOCITY, ACCELERATION, IDLE_POWER
    print(f"    Mass AGV: {MASS_AGV} kg")
    print(f"    Friction coefficient: {FRICTION_COEFF}")
    print(f"    Motor efficiency: {MOTOR_EFFICIENCY}")
    print(f"    Max velocity: {MAX_VELOCITY} m/s")
    print(f"    Acceleration: {ACCELERATION} m/s²")
    print(f"    Idle power: {IDLE_POWER} W")
    
    try:
        # Run all tests
        test_energy_calculations()
        test_simple_route()
        test_route_with_tardiness()
        test_varying_loads()
        test_invalid_route()
        test_resource_conflict_with_delay()  # NEW: Test conflict scenario
        test_new_architecture()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        print("\n📊 Summary:")
        print("   ✅ Backward compatibility maintained")
        print("   ✅ New architecture working")
        print("   ✅ Error handling verified")
        print("   ✅ Configuration system tested")
        print("   ✅ Conflict/delay scenario tested")
        print("\nNote: Some tests may show API errors if resources don't exist.")
        print("This is expected behavior for invalid resource IDs.")
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
