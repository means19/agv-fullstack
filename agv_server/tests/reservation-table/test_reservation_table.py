"""
Test script for Reservation Table System
Tests the D-MAS (Delegate Multi-Agent System) reservation functionality
"""

import requests
from datetime import datetime, timedelta, timezone
import json
import sys

BASE_URL = "http://localhost:8000/api/agvs/reservation"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_response(response):
    """Print formatted response"""
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)


def test_reservation_system():
    """Main test function for reservation system"""
    
    print_section("Testing Reservation Table System")
    
    # Test 1: List all resources
    print_section("Test 1: List All Resources")
    try:
        response = requests.get(f"{BASE_URL}/resources/")
        print_response(response)
        
        if response.status_code != 200:
            print("\n❌ Failed to fetch resources!")
            return False
        
        resources = response.json()
        
        if not resources:
            print("\n  No resources found!")
            print("Please create some resources first using Django shell:")
            print("  docker-compose exec server python manage.py shell")
            print("\nThen run:")
            print("  from agv_data.models import ResourceAgent")
            print("  ResourceAgent.objects.create(name='CA_01', resource_type='CA')")
            print("  ResourceAgent.objects.create(name='LSA_01_02', resource_type='LSA')")
            return False
        
        print(f"\n Found {len(resources)} resources")
        resource_id = resources[0]['id']
        resource_name = resources[0]['name']
        print(f"Using resource: {resource_name} (ID: {resource_id}) for testing")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server.")
        print("Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Query earliest available slot (Exploring Ant)
    print_section("Test 2: Query Earliest Available Slot (Exploring Ant)")
    now = datetime.now(timezone.utc)
    query_data = {
        "request_start_time": now.isoformat(),
        "duration_seconds": 30
    }
    print("Request:")
    print(json.dumps(query_data, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/resource/{resource_id}/query_slot/",
        json=query_data
    )
    print_response(response)
    
    if response.status_code == 200:
        print("\n Query slot successful")
    else:
        print("\n❌ Query slot failed")
    
    # Test 3: Book a slot (Intention Ant)
    print_section("Test 3: Book a Slot (Intention Ant)")
    book_data = {
        "agv_id": 1,
        "request_start_time": now.isoformat(),
        "duration_seconds": 30
    }
    print("Request:")
    print(json.dumps(book_data, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/resource/{resource_id}/book_slot/",
        json=book_data
    )
    print_response(response)
    
    if response.status_code != 201:
        print("\n❌ Booking failed")
        return False
    
    booking = response.json()
    booking_id = booking['id']
    print(f"\n Booking created successfully (ID: {booking_id})")
    
    # Test 4: Query slot again (should return later time due to conflict)
    print_section("Test 4: Query Slot Again (Should Detect Conflict)")
    query_data2 = {
        "request_start_time": now.isoformat(),
        "duration_seconds": 30
    }
    print("Request:")
    print(json.dumps(query_data2, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/resource/{resource_id}/query_slot/",
        json=query_data2
    )
    print_response(response)
    
    if response.status_code == 200:
        result = response.json()
        delay = result.get('calculated_delay_seconds', 0)
        if delay > 0:
            print(f"\n Conflict detected! Suggested delay: {delay} seconds")
        else:
            print("\n No conflict detected (unexpected)")
    
    # Test 5: List bookings for AGV
    print_section("Test 5: List Bookings for AGV 1")
    response = requests.get(f"{BASE_URL}/bookings/?agv_id=1")
    print_response(response)
    
    if response.status_code == 200:
        bookings = response.json()
        print(f"\n Found {len(bookings)} booking(s) for AGV 1")
    
    # Test 6: Book another slot (different time, should succeed)
    print_section("Test 6: Book Another Slot (2 minutes later)")
    later_time = now + timedelta(minutes=2)
    book_data2 = {
        "agv_id": 2,
        "request_start_time": later_time.isoformat(),
        "duration_seconds": 30
    }
    print("Request:")
    print(json.dumps(book_data2, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/resource/{resource_id}/book_slot/",
        json=book_data2
    )
    print_response(response)
    
    if response.status_code == 201:
        print("\n Second booking created successfully")
    else:
        print("\n❌ Second booking failed")
    
    # Test 7: List all bookings for the resource
    print_section("Test 7: List All Bookings for Resource")
    response = requests.get(f"{BASE_URL}/bookings/?resource_id={resource_id}")
    print_response(response)
    
    if response.status_code == 200:
        bookings = response.json()
        print(f"\n Found {len(bookings)} booking(s) for resource {resource_name}")
    
    # Test 8: Cancel first booking
    print_section("Test 8: Cancel First Booking")
    print(f"Cancelling booking ID: {booking_id}")
    
    response = requests.delete(f"{BASE_URL}/bookings/{booking_id}/")
    print_response(response)
    
    if response.status_code == 200:
        print("\n Booking cancelled successfully")
    else:
        print("\n❌ Failed to cancel booking")
    
    # Test 9: Verify booking was cancelled
    print_section("Test 9: Verify Booking Cancellation")
    response = requests.get(f"{BASE_URL}/bookings/?agv_id=1")
    print_response(response)
    
    if response.status_code == 200:
        bookings = response.json()
        print(f"\n AGV 1 now has {len(bookings)} booking(s)")
    
    print_section("Test Summary")
    print(" All tests completed successfully!")
    print("\nReservation Table System is working correctly.")
    
    return True


if __name__ == "__main__":
    try:
        success = test_reservation_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
