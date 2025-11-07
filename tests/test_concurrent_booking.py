"""
Concurrent Booking Test - Race Condition Test
Tests if the Reservation Table can handle multiple simultaneous booking requests correctly.

This test simulates 10 "Intention Ants" trying to book the same resource at the same time.
Expected result: Only 1 should succeed (201), others should get conflict (409).
"""

import requests
import threading
import time
from datetime import datetime, timezone, timedelta
import json
from collections import Counter

BASE_URL = "http://localhost:8000/api/agvs/reservation"

# Results storage (thread-safe with lock)
results_lock = threading.Lock()
results = []


def book_slot_concurrent(agv_id, resource_id, start_time_iso, duration_seconds, thread_id):
    """
    Function to be called by each thread - simulates an Intention Ant
    """
    try:
        book_data = {
            "agv_id": agv_id,
            "request_start_time": start_time_iso,
            "duration_seconds": duration_seconds
        }
        
        # Make the request
        response = requests.post(
            f"{BASE_URL}/resource/{resource_id}/book_slot/",
            json=book_data,
            timeout=10
        )
        
        # Store result (thread-safe)
        with results_lock:
            results.append({
                "thread_id": thread_id,
                "agv_id": agv_id,
                "status_code": response.status_code,
                "response": response.json() if response.status_code in [201, 409, 400] else response.text,
                "timestamp": time.time()
            })
        
        # Print immediate feedback
        if response.status_code == 201:
            print(f"  ✅ Thread {thread_id} (AGV {agv_id}): SUCCESS - Booking created!")
        elif response.status_code == 409:
            print(f"  ⚠️  Thread {thread_id} (AGV {agv_id}): CONFLICT - As expected")
        else:
            print(f"  ❌ Thread {thread_id} (AGV {agv_id}): Unexpected status {response.status_code}")
            
    except Exception as e:
        with results_lock:
            results.append({
                "thread_id": thread_id,
                "agv_id": agv_id,
                "status_code": None,
                "response": str(e),
                "timestamp": time.time()
            })
        print(f"  ❌ Thread {thread_id} (AGV {agv_id}): Exception - {str(e)}")


def test_concurrent_booking():
    """
    Main test function for concurrent booking
    """
    print("="*70)
    print("  CONCURRENT BOOKING TEST - Race Condition Simulation")
    print("="*70)
    print()
    
    # Step 1: Get available resources
    print("Step 1: Finding an available resource...")
    try:
        response = requests.get(f"{BASE_URL}/resources/")
        if response.status_code != 200:
            print(f"❌ Failed to fetch resources: {response.status_code}")
            return False
        
        resources = response.json()
        if len(resources) < 2:
            print("❌ Need at least 2 resources. Run create_sample_resources.py first.")
            return False
        
        # Use resource ID 2 (or first LSA)
        test_resource = None
        for resource in resources:
            if resource['id'] == 2:
                test_resource = resource
                break
        
        if not test_resource:
            test_resource = resources[1]  # Use second resource
        
        resource_id = test_resource['id']
        resource_name = test_resource['name']
        
        print(f"✅ Using resource: {resource_name} (ID: {resource_id})")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Step 2: Clear any existing bookings for this resource
    print("Step 2: Checking for existing bookings...")
    try:
        response = requests.get(f"{BASE_URL}/bookings/?resource_id={resource_id}")
        existing_bookings = response.json()
        print(f"Found {len(existing_bookings)} existing booking(s)")
        
        # Cancel old bookings if any
        for booking in existing_bookings:
            # Parse the end_time to check if it's in the past
            booking_id = booking['id']
            requests.delete(f"{BASE_URL}/bookings/{booking_id}/")
        print("✅ Cleared existing bookings")
        print()
    except Exception as e:
        print(f"⚠️  Could not clear bookings: {e}")
        print()
    
    # Step 3: Setup test parameters
    num_threads = 10
    start_time = datetime.now(timezone.utc) + timedelta(minutes=5)  # 5 minutes from now
    start_time_iso = start_time.isoformat()
    duration_seconds = 30
    
    print("Step 3: Test Configuration")
    print(f"  Number of concurrent requests: {num_threads}")
    print(f"  Target resource: {resource_name} (ID: {resource_id})")
    print(f"  Requested start time: {start_time_iso}")
    print(f"  Duration: {duration_seconds} seconds")
    print()
    
    # Step 4: Launch concurrent threads
    print("Step 4: Launching concurrent booking requests...")
    print("-" * 70)
    
    threads = []
    start_time_threads = time.time()
    
    for i in range(num_threads):
        agv_id = 100 + i  # AGV IDs: 100-109
        thread = threading.Thread(
            target=book_slot_concurrent,
            args=(agv_id, resource_id, start_time_iso, duration_seconds, i+1)
        )
        threads.append(thread)
    
    # Start all threads nearly simultaneously
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    elapsed_time = time.time() - start_time_threads
    
    print("-" * 70)
    print(f"All threads completed in {elapsed_time:.3f} seconds")
    print()
    
    # Step 5: Analyze results
    print("Step 5: Analyzing Results")
    print("="*70)
    
    status_counter = Counter([r['status_code'] for r in results])
    
    print(f"\nStatus Code Distribution:")
    for status_code, count in sorted(status_counter.items()):
        if status_code == 201:
            print(f"  ✅ 201 (Created):   {count} request(s)")
        elif status_code == 409:
            print(f"  ⚠️  409 (Conflict):  {count} request(s)")
        elif status_code is None:
            print(f"  ❌ Exception:       {count} request(s)")
        else:
            print(f"  ❓ {status_code}:           {count} request(s)")
    
    # Detailed results
    print(f"\nDetailed Results:")
    success_count = 0
    conflict_count = 0
    error_count = 0
    
    for result in sorted(results, key=lambda x: x['timestamp']):
        thread_id = result['thread_id']
        agv_id = result['agv_id']
        status = result['status_code']
        
        if status == 201:
            success_count += 1
            booking_id = result['response'].get('id', 'N/A')
            print(f"  Thread {thread_id:2d} (AGV {agv_id}): ✅ SUCCESS (Booking ID: {booking_id})")
        elif status == 409:
            conflict_count += 1
            print(f"  Thread {thread_id:2d} (AGV {agv_id}): ⚠️  CONFLICT (Expected)")
        else:
            error_count += 1
            print(f"  Thread {thread_id:2d} (AGV {agv_id}): ❌ ERROR (Status: {status})")
    
    # Step 6: Verdict
    print()
    print("="*70)
    print("  FINAL VERDICT")
    print("="*70)
    
    print(f"\nSummary:")
    print(f"  Total requests:     {num_threads}")
    print(f"  Successful:         {success_count}")
    print(f"  Conflicts (409):    {conflict_count}")
    print(f"  Errors:             {error_count}")
    
    # Check if result meets expectations
    if success_count == 1:
        print(f"\n{'✅'*10}")
        print(f"✅ TEST PASSED! Exactly 1 booking succeeded.")
        print(f"✅ Concurrency control is working PERFECTLY!")
        print(f"{'✅'*10}")
        
        if conflict_count == num_threads - 1:
            print(f"\n🎯 PERFECT SCORE: All {conflict_count} other requests got 409 Conflict!")
        else:
            print(f"\n⚠️  Note: {conflict_count} requests got 409, others may have different errors")
        
        return True
        
    elif success_count == 0:
        print(f"\n❌ TEST FAILED: No bookings succeeded!")
        print(f"   This might indicate a server error or all requests conflicted with existing data.")
        return False
        
    elif success_count > 1:
        print(f"\n❌ TEST FAILED: {success_count} bookings succeeded!")
        print(f"   CRITICAL: Race condition detected! Multiple bookings for same slot.")
        print(f"   Transaction isolation is NOT working correctly.")
        return False
    
    return False


def main():
    """Entry point"""
    try:
        print("\n")
        success = test_concurrent_booking()
        print("\n")
        
        if success:
            print("🚀 Your Reservation Table is ready for production!")
            print("   It can handle concurrent requests from multiple AGVs safely.")
        else:
            print("⚠️  Please review the results above.")
        
        print("\n")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
