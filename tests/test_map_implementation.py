"""
Test script for Map implementation.
Run this after:
1. docker compose up -d
2. docker compose exec django_app python manage.py migrate
3. docker compose exec django_app python manage.py import_map

Usage:
python test_map_implementation.py
"""

import requests
import json


BASE_URL = "http://localhost:8000/api/agvs"


def test_map_layout():
    """Test GET /api/agvs/map/layout/"""
    print("\n" + "="*60)
    print("TEST 1: Get Map Layout")
    print("="*60)
    
    url = f"{BASE_URL}/map/layout/"
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"Total Nodes: {data['stats']['num_nodes']}")
        print(f"  - CA: {data['stats']['num_ca']}")
        print(f"  - DEPOT: {data['stats']['num_depot']}")
        print(f"  - STATION: {data['stats']['num_station']}")
        print(f"Total Edges (LSA): {data['stats']['num_edges']}")
        
        print("\nSample Nodes:")
        for node in data['nodes'][:3]:
            print(f"  - {node['name']} ({node['type']}) at ({node['x']}, {node['y']})")
        
        print("\nSample Edges:")
        for edge in data['edges'][:3]:
            print(f"  - {edge['name']}: {edge['from']} → {edge['to']} ({edge['distance_m']}m)")
        
        return True
    else:
        print(f"❌ Failed!")
        print(response.text)
        return False


def test_ideal_path():
    """Test GET /api/agvs/map/path/"""
    print("\n" + "="*60)
    print("TEST 2: Get Ideal Path (Dijkstra)")
    print("="*60)
    
    # Test case: CA-01 to STATION-A
    start = "CA-01"
    end = "STATION-A"
    speed = 1.5  # 1.5 m/s
    
    url = f"{BASE_URL}/map/path/?start={start}&end={end}&speed={speed}"
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    print(f"Route: {start} → {end} @ {speed} m/s")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"Total Distance: {data['total_distance_m']:.2f} m")
        print(f"Total Time: {data['total_time_sec']:.2f} sec ({data['total_time_sec']/60:.2f} min)")
        print(f"Number of Steps: {data['num_steps']}")
        
        print("\nRoute Steps:")
        for i, step in enumerate(data['path']):
            print(f"  {i+1}. {step['node_name']} ({step['resource_type']})")
            if step['distance_m'] > 0:
                print(f"     → Travel {step['distance_m']:.1f}m in {step['travel_time_sec']:.1f}sec")
        
        return True
    else:
        print(f"❌ Failed!")
        print(response.text)
        return False


def test_path_variations():
    """Test different path queries"""
    print("\n" + "="*60)
    print("TEST 3: Path Variations")
    print("="*60)
    
    test_cases = [
        ("CA-01", "CA-06", 1.0),
        ("DEPOT-01", "STATION-B", 2.0),
        ("STATION-A", "DEPOT-02", 1.5),
    ]
    
    for start, end, speed in test_cases:
        url = f"{BASE_URL}/map/path/?start={start}&end={end}&speed={speed}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {start} → {end}: {data['total_distance_m']:.1f}m in {data['total_time_sec']:.1f}sec")
        else:
            print(f"❌ {start} → {end}: FAILED")
            print(f"   Error: {response.json().get('error', 'Unknown error')}")


def test_error_cases():
    """Test error handling"""
    print("\n" + "="*60)
    print("TEST 4: Error Handling")
    print("="*60)
    
    # Missing parameters
    print("Test 4.1: Missing parameters")
    response = requests.get(f"{BASE_URL}/map/path/?start=CA-01")
    print(f"  Status: {response.status_code} (expected 400)")
    
    # Invalid node
    print("Test 4.2: Invalid node")
    response = requests.get(f"{BASE_URL}/map/path/?start=CA-99&end=CA-01&speed=1.0")
    print(f"  Status: {response.status_code} (expected 404)")
    
    # Invalid speed
    print("Test 4.3: Invalid speed")
    response = requests.get(f"{BASE_URL}/map/path/?start=CA-01&end=CA-02&speed=0")
    print(f"  Status: {response.status_code} (expected 400)")


def main():
    print("\n" + "="*60)
    print("MAP IMPLEMENTATION TEST SUITE")
    print("="*60)
    print("\nPrerequisites:")
    print("1. docker compose up -d")
    print("2. docker compose exec django_app python manage.py migrate")
    print("3. docker compose exec django_app python manage.py import_map")
    print("\nTesting server at:", BASE_URL)
    
    try:
        # Run tests
        test_map_layout()
        test_ideal_path()
        test_path_variations()
        test_error_cases()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server!")
        print("Make sure Docker is running and server is accessible at:", BASE_URL)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
