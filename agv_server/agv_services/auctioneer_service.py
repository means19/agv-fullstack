"""
Auctioneer Service - Calculate Baseline Costs

This module implements the Auctioneer's role in the SSI-DMAS-ET auction system.
The Auctioneer calculates baseline costs (E_baseline, TFT_baseline) for new tasks
using ideal Dijkstra routing (without D-MAS delays).

These baseline values are used by AGV agents for dynamic normalization of bids.
"""

from typing import Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agv_data.agv_agent_constants import (
    C_BASE,
    C_LOAD_COEFF,
    FALLBACK_NORM_ENERGY_KJ,
    FALLBACK_NORM_TFT_SEC
)


# Configuration
DEPOT_LOCATION_NAME = "DEPOT_STATION"  # TODO: Configure based on your system


def calculate_baseline_simple(
    depot_to_pickup_distance_m: float,
    depot_to_pickup_time_s: float,
    pickup_to_delivery_distance_m: float,
    pickup_to_delivery_time_s: float,
    load_kg: float
) -> Tuple[float, float]:
    """
    Calculate baseline costs (E_baseline, TFT_baseline) for a task using simple distance/time inputs.
    
    This is a simplified version that doesn't require Dijkstra integration.
    Use this when you already have path distances and times.
    
    Args:
        depot_to_pickup_distance_m: Distance from depot to pickup location (meters)
        depot_to_pickup_time_s: Time from depot to pickup location (seconds)
        pickup_to_delivery_distance_m: Distance from pickup to delivery (meters)
        pickup_to_delivery_time_s: Time from pickup to delivery (seconds)
        load_kg: Load weight in kilograms
        
    Returns:
        Tuple[float, float]: (E_baseline in kJ, TFT_baseline in seconds)
        Returns (inf, inf) if calculation fails
        
    Example:
        >>> E_base, TFT_base = calculate_baseline_simple(
        ...     depot_to_pickup_distance_m=100.0,
        ...     depot_to_pickup_time_s=60.0,
        ...     pickup_to_delivery_distance_m=150.0,
        ...     pickup_to_delivery_time_s=90.0,
        ...     load_kg=200.0
        ... )
        >>> print(f"E_baseline: {E_base:.2f} kJ, TFT_baseline: {TFT_base:.2f}s")
    """
    try:
        # Segment 1: Depot -> Pickup (empty AGV, load = 0)
        e1_travel = (C_BASE + C_LOAD_COEFF * 0) * depot_to_pickup_distance_m
        t1 = depot_to_pickup_time_s
        
        # Segment 2: Pickup -> Delivery (loaded AGV)
        e2_travel = (C_BASE + C_LOAD_COEFF * load_kg) * pickup_to_delivery_distance_m
        t2 = pickup_to_delivery_time_s
        
        # Total baseline costs
        E_baseline = e1_travel + e2_travel
        TFT_baseline = t1 + t2
        
        # Apply fallback if zero
        if E_baseline == 0:
            E_baseline = FALLBACK_NORM_ENERGY_KJ
        if TFT_baseline == 0:
            TFT_baseline = FALLBACK_NORM_TFT_SEC
        
        return E_baseline, TFT_baseline
    
    except Exception as e:
        print(f"[ERROR] calculate_baseline_simple failed: {e}")
        return float('inf'), float('inf')


def calculate_baseline_from_route_data(
    route_data: dict
) -> Tuple[float, float]:
    """
    Calculate baseline from a route data dictionary.
    
    Args:
        route_data: Dictionary containing:
            - 'segment_1': {'distance_m': float, 'time_s': float}
            - 'segment_2': {'distance_m': float, 'time_s': float}
            - 'load_kg': float
            
    Returns:
        Tuple[float, float]: (E_baseline, TFT_baseline)
        
    Example:
        >>> route_data = {
        ...     'segment_1': {'distance_m': 100.0, 'time_s': 60.0},
        ...     'segment_2': {'distance_m': 150.0, 'time_s': 90.0},
        ...     'load_kg': 200.0
        ... }
        >>> E_base, TFT_base = calculate_baseline_from_route_data(route_data)
    """
    try:
        seg1 = route_data['segment_1']
        seg2 = route_data['segment_2']
        load_kg = route_data['load_kg']
        
        return calculate_baseline_simple(
            depot_to_pickup_distance_m=seg1['distance_m'],
            depot_to_pickup_time_s=seg1['time_s'],
            pickup_to_delivery_distance_m=seg2['distance_m'],
            pickup_to_delivery_time_s=seg2['time_s'],
            load_kg=load_kg
        )
    
    except (KeyError, TypeError) as e:
        print(f"[ERROR] Invalid route_data structure: {e}")
        return float('inf'), float('inf')


# TODO: Implement Dijkstra integration when pathfinding module is ready
# def calculate_baseline_dijkstra(
#     pickup_location: str,
#     delivery_location: str,
#     load_kg: float
# ) -> Tuple[float, float]:
#     """
#     Calculate baseline using Dijkstra pathfinding (future implementation).
#     
#     This will integrate with your existing pathfinding module to calculate
#     optimal paths from depot to pickup and pickup to delivery.
#     
#     Args:
#         pickup_location: Name/ID of pickup location
#         delivery_location: Name/ID of delivery location
#         load_kg: Load weight in kilograms
#         
#     Returns:
#         Tuple[float, float]: (E_baseline, TFT_baseline)
#     """
#     from pathfinding.dijkstra import Dijkstra  # Import when available
#     
#     try:
#         # Segment 1: Depot -> Pickup (empty)
#         route_1 = Dijkstra.find_path(DEPOT_LOCATION_NAME, pickup_location)
#         d1_meters = route_1.total_distance
#         t1_seconds = route_1.total_time
#         
#         e1_travel = (C_BASE + C_LOAD_COEFF * 0) * d1_meters
#         
#         # Segment 2: Pickup -> Delivery (loaded)
#         route_2 = Dijkstra.find_path(pickup_location, delivery_location)
#         d2_meters = route_2.total_distance
#         t2_seconds = route_2.total_time
#         
#         e2_travel = (C_BASE + C_LOAD_COEFF * load_kg) * d2_meters
#         
#         # Total baseline
#         E_baseline = e1_travel + e2_travel
#         TFT_baseline = t1_seconds + t2_seconds
#         
#         # Apply fallback if zero
#         if E_baseline == 0:
#             E_baseline = FALLBACK_NORM_ENERGY_KJ
#         if TFT_baseline == 0:
#             TFT_baseline = FALLBACK_NORM_TFT_SEC
#         
#         return E_baseline, TFT_baseline
#     
#     except Exception as e:
#         print(f"[ERROR] calculate_baseline_dijkstra failed: {e}")
#         return float('inf'), float('inf')


if __name__ == "__main__":
    # Example usage
    print("="*60)
    print("AUCTIONEER SERVICE - BASELINE CALCULATION TEST")
    print("="*60)
    
    # Test case 1: Simple calculation
    print("\nTest 1: Simple baseline calculation")
    E_base, TFT_base = calculate_baseline_simple(
        depot_to_pickup_distance_m=100.0,
        depot_to_pickup_time_s=60.0,
        pickup_to_delivery_distance_m=150.0,
        pickup_to_delivery_time_s=90.0,
        load_kg=200.0
    )
    print(f"  E_baseline: {E_base:.6f} kJ")
    print(f"  TFT_baseline: {TFT_base:.2f} seconds")
    
    # Manual calculation for verification
    e1 = (C_BASE + C_LOAD_COEFF * 0) * 100.0
    e2 = (C_BASE + C_LOAD_COEFF * 200.0) * 150.0
    expected_E = e1 + e2
    expected_TFT = 60.0 + 90.0
    print(f"  Expected E: {expected_E:.6f} kJ")
    print(f"  Expected TFT: {expected_TFT:.2f} seconds")
    print(f"  Match: {abs(E_base - expected_E) < 0.001 and abs(TFT_base - expected_TFT) < 0.001}")
    
    # Test case 2: Route data format
    print("\nTest 2: Route data format")
    route_data = {
        'segment_1': {'distance_m': 100.0, 'time_s': 60.0},
        'segment_2': {'distance_m': 150.0, 'time_s': 90.0},
        'load_kg': 200.0
    }
    E_base2, TFT_base2 = calculate_baseline_from_route_data(route_data)
    print(f"  E_baseline: {E_base2:.6f} kJ")
    print(f"  TFT_baseline: {TFT_base2:.2f} seconds")
    print(f"  Match with Test 1: {E_base == E_base2 and TFT_base == TFT_base2}")
    
    # Test case 3: Zero values (should use fallback)
    print("\nTest 3: Zero values (fallback test)")
    E_base3, TFT_base3 = calculate_baseline_simple(0, 0, 0, 0, 0)
    print(f"  E_baseline: {E_base3:.6f} kJ (should be {FALLBACK_NORM_ENERGY_KJ})")
    print(f"  TFT_baseline: {TFT_base3:.2f} s (should be {FALLBACK_NORM_TFT_SEC})")
    print(f"  Fallback working: {E_base3 == FALLBACK_NORM_ENERGY_KJ and TFT_base3 == FALLBACK_NORM_TFT_SEC}")
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
