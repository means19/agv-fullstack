"""
Auctioneer Service - Calculate Baseline Costs

This module implements the Auctioneer's role in the SSI-DMAS-ET auction system.
The Auctioneer calculates baseline costs (E_baseline, TFT_baseline) for new tasks
using ideal Dijkstra routing (without D-MAS delays).

These baseline values are used by AGV agents for dynamic normalization of bids.

Reference: docs/auction-logic/auction-logic-implementation-guide.md
"""

from typing import Tuple, Optional
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
DEPOT_LOCATION_NAME = "DEPOT-01"  # Default depot location
DEFAULT_LOAD_KG = 100.0  # Default load weight for orders


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


def _node_number_to_name(node_num: int) -> Optional[str]:
    """
    Convert a node number (from Order model) to a ResourceAgent name.
    
    Args:
        node_num: Node number (e.g., 1, 2, 3, ...)
        
    Returns:
        str: Node name (e.g., "CA-01", "CA-02", ...) or None if not found
        
    Note:
        - CA (Crossroad Agents) are numbered: 1 → "CA-01", 2 → "CA-02", etc.
        - DEPOT and STATION nodes need to be looked up by their specific purpose
        - This function checks both naming convention and database lookup
    """
    try:
        from agv_data.models import ResourceAgent
        
        # Try CA naming convention first (most common)
        ca_name = f"CA-{node_num:02d}"
        if ResourceAgent.objects.filter(name=ca_name).exists():
            return ca_name
        
        # If not a CA, it might be a DEPOT or STATION
        # Query ResourceAgents with similar naming patterns
        # Look for nodes that might match the number
        
        # Common patterns:
        # - DEPOT nodes might be stored differently
        # - STATION nodes might be stored differently
        
        # For now, if it's not a standard CA, return None
        # (Can be extended to handle DEPOT/STATION lookup)
        print(f"[WARNING] Node {node_num} does not match CA naming. May be DEPOT/STATION.")
        return None
        
    except Exception as e:
        print(f"[ERROR] _node_number_to_name failed: {e}")
        return None


def calculate_baseline_from_order(order) -> Tuple[float, float]:
    """
    Calculate baseline costs for an Order using MapService and Dijkstra pathfinding.
    
    This is the MAIN implementation of Algorithm A (CALCULATE_BASELINE) from the specification.
    
    Args:
        order: Order object with storage_node (pickup) and workstation_node (delivery)
        
    Returns:
        Tuple[float, float]: (E_baseline in kJ, TFT_baseline in seconds)
        Returns (inf, inf) if calculation fails
        
    Algorithm:
        1. Get node names from order's storage_node and workstation_node numbers
        2. Calculate Leg 1: DEPOT -> Pickup (empty load = 0)
           - Get ideal path via MapService.get_ideal_path()
           - Calculate E1 = (C_BASE + 0) * distance1
           - Get T1 from path
        3. Calculate Leg 2: Pickup -> Delivery (loaded)
           - Get ideal path via MapService.get_ideal_path()
           - Calculate E2 = (C_BASE + C_LOAD_COEFF * load) * distance2
           - Get T2 from path
        4. Sum totals: E_baseline = E1 + E2, TFT_baseline = T1 + T2
        5. Apply fallback if any value is 0
    """
    try:
        # Import here to avoid circular dependency
        from agv_data.services import MapService
        
        # Initialize MapService
        map_service = MapService()
        if map_service._graph is None:
            map_service.load_graph()
        
        print(f"\n{'='*60}")
        print(f"[AuctioneerService] Calculating Baseline for Order {order.order_id}")
        print(f"{'='*60}")
        
        # Convert node numbers to names
        pickup_loc = _node_number_to_name(order.storage_node)
        delivery_loc = _node_number_to_name(order.workstation_node)
        
        if pickup_loc is None:
            print(f"[ERROR] Cannot map storage_node {order.storage_node} to a node name")
            return float('inf'), float('inf')
        
        if delivery_loc is None:
            print(f"[ERROR] Cannot map workstation_node {order.workstation_node} to a node name")
            return float('inf'), float('inf')
        
        print(f"Pickup: {pickup_loc} (node {order.storage_node})")
        print(f"Delivery: {delivery_loc} (node {order.workstation_node})")
        
        # Determine load (can be extended to Order model later)
        load_kg = DEFAULT_LOAD_KG
        print(f"Load: {load_kg} kg")
        
        # Convert parking_node to name
        parking_loc = _node_number_to_name(order.parking_node)
        if parking_loc is None:
            print(f"[ERROR] Cannot map parking_node {order.parking_node} to name")
            return float('inf'), float('inf')
        
        print(f"Parking (reference start): {parking_loc} (node {order.parking_node})")
        
        # === LEG 1: Parking -> Pickup (Empty) ===
        # This is the IDEAL reference route (no obstacles, from parking)
        print(f"\nLeg 1: {parking_loc} -> {pickup_loc} (EMPTY - IDEAL REFERENCE)")
        
        path1_result = map_service.get_ideal_path(parking_loc, pickup_loc)
        
        if path1_result is None or len(path1_result) == 0:
            print(f"[ERROR] No path found for Leg 1")
            return float('inf'), float('inf')
        
        # Extract total distance and time from last RouteStep
        last_step_1 = path1_result[-1]
        d1_meters = last_step_1.cumulative_distance_m
        t1_seconds = last_step_1.cumulative_time_sec
        
        # Energy for empty leg (no load)
        e1_travel = (C_BASE + C_LOAD_COEFF * 0) * d1_meters
        
        print(f"  Distance: {d1_meters:.2f} m")
        print(f"  Time: {t1_seconds:.2f} s")
        print(f"  Energy: {e1_travel:.4f} kJ")
        
        # === LEG 2: Pickup -> Delivery (Loaded) ===
        print(f"\nLeg 2: {pickup_loc} -> {delivery_loc} (LOADED {load_kg} kg)")
        
        path2_result = map_service.get_ideal_path(pickup_loc, delivery_loc)
        
        if path2_result is None or len(path2_result) == 0:
            print(f"[ERROR] No path found for Leg 2")
            return float('inf'), float('inf')
        
        # Extract total distance and time from last RouteStep
        last_step_2 = path2_result[-1]
        d2_meters = last_step_2.cumulative_distance_m
        t2_seconds = last_step_2.cumulative_time_sec
        
        # Energy for loaded leg
        e2_travel = (C_BASE + C_LOAD_COEFF * load_kg) * d2_meters
        
        print(f"  Distance: {d2_meters:.2f} m")
        print(f"  Time: {t2_seconds:.2f} s")
        print(f"  Energy: {e2_travel:.4f} kJ")
        
        # === CALCULATE BASELINE TOTALS ===
        E_baseline = e1_travel + e2_travel
        TFT_baseline = t1_seconds + t2_seconds
        
        # Apply fallback if zero (to avoid division by zero in normalization)
        if E_baseline == 0:
            print(f"[WARNING] E_baseline is 0, using fallback")
            E_baseline = FALLBACK_NORM_ENERGY_KJ
        if TFT_baseline == 0:
            print(f"[WARNING] TFT_baseline is 0, using fallback")
            TFT_baseline = FALLBACK_NORM_TFT_SEC
        
        print(f"\n{'='*60}")
        print(f"BASELINE RESULTS:")
        print(f"  E_baseline  = {E_baseline:.4f} kJ")
        print(f"  TFT_baseline = {TFT_baseline:.2f} sec ({TFT_baseline/60:.2f} min)")
        print(f"{'='*60}\n")
        
        return E_baseline, TFT_baseline
        
    except Exception as e:
        print(f"[FATAL ERROR] calculate_baseline_from_order: {e}")
        import traceback
        traceback.print_exc()
        return float('inf'), float('inf')


# Singleton instance for easy access
class AuctioneerService:
    """
    Service class for auction baseline calculations.
    Provides both simple (manual) and integrated (MapService) baseline calculations.
    """
    
    @staticmethod
    def calculate_baseline(order) -> Tuple[float, float]:
        """
        Main entry point: Calculate baseline for an Order.
        Uses MapService integration with Dijkstra pathfinding.
        """
        return calculate_baseline_from_order(order)
    
    @staticmethod
    def calculate_baseline_manual(
        depot_to_pickup_distance_m: float,
        depot_to_pickup_time_s: float,
        pickup_to_delivery_distance_m: float,
        pickup_to_delivery_time_s: float,
        load_kg: float
    ) -> Tuple[float, float]:
        """
        Calculate baseline with manual distance/time inputs (for testing).
        """
        return calculate_baseline_simple(
            depot_to_pickup_distance_m,
            depot_to_pickup_time_s,
            pickup_to_delivery_distance_m,
            pickup_to_delivery_time_s,
            load_kg
        )


# Singleton instance
auctioneer_service = AuctioneerService()


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
