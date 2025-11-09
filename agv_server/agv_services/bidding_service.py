"""
Bidding Service - Calculate AGV Bids with Dynamic Normalization

This module implements the bidding logic for AGV agents in the SSI-DMAS-ET system.
It uses dynamic baseline normalization to ensure fair comparison of bids across different tasks.

Key concepts:
- Marginal cost: Additional cost for accepting a new task
- Normalization: Divide by baseline to get scale-free efficiency score
- Hybrid objective: Balance between MiniSum (efficiency) and MiniMax (load balancing)

Reference: docs/auction-logic/auction-logic-implementation-guide.md - Section 2
"""

from typing import Tuple, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agv_data.agv_agent import DMAS_ET_silent, RouteStep
from agv_data.agv_agent_constants import (
    K_ENERGY,
    K_TIME,
    EPSILON,
    FALLBACK_NORM_ENERGY_KJ,
    FALLBACK_NORM_TFT_SEC,
    C_BASE,
    C_LOAD_COEFF
)
from datetime import datetime, timezone, timedelta


DEFAULT_LOAD_KG = 100.0  # Default load weight for orders
MIN_DURATION_SEC = 1.0  # Minimum reservation duration


def _get_completion_node_from_remaining_path(agv) -> Optional[int]:
    """
    Get the node where AGV will complete its current task.
    
    Args:
        agv: AGV object with remaining_path
        
    Returns:
        int: Node number where current task completes, or None if idle
    """
    if not agv.remaining_path or len(agv.remaining_path) == 0:
        return None
    
    # Last node in remaining path is where AGV completes current task
    return agv.remaining_path[-1]


def _calculate_j1_for_busy_agv(
    agv,
    auction_start_time: datetime
) -> Tuple[float, float]:
    """
    Calculate J1 (current task costs) for a busy AGV.
    
    For busy AGV:
    - J1 = costs to complete current task (from now until completion)
    - Uses remaining_path and DMAS_ET to calculate
    
    Args:
        agv: AGV object (may be IDLE or MOVING/WAITING)
        auction_start_time: Time when auction starts (= time new task assigned)
        
    Returns:
        Tuple[float, float]: (E_j1, TFT_j1) - costs for current task
        Returns (0.0, 0.0) if AGV is idle
    """
    # If AGV is IDLE, J1 = 0
    if agv.motion_state == 0:  # IDLE
        return 0.0, 0.0
    
    # If no remaining path, treat as idle
    if not agv.remaining_path or len(agv.remaining_path) == 0:
        return 0.0, 0.0
    
    try:
        from agv_data.models import ResourceAgent
        
        # Convert remaining_path (node numbers) to RouteSteps
        route_steps = []
        
        for i, node_num in enumerate(agv.remaining_path):
            # Convert node number to name
            node_name = f"CA-{node_num:02d}"
            
            try:
                resource = ResourceAgent.objects.get(name=node_name)
            except ResourceAgent.DoesNotExist:
                print(f"[WARNING] Node {node_num} ({node_name}) not found in remaining path")
                continue
            
            # Estimate duration (simplified - could be improved with actual travel times)
            duration = MIN_DURATION_SEC
            
            # Determine if this is task endpoint (last node in path)
            is_endpoint = (i == len(agv.remaining_path) - 1)
            
            # Determine load (if on outbound journey, may be loaded)
            load_kg = 0.0
            if agv.journey_phase == 0:  # OUTBOUND
                # If we have active_order, check if we're past pickup
                if agv.active_order:
                    storage_node = agv.active_order.storage_node
                    # If current position is past storage, we're loaded
                    if agv.current_node and agv.current_node >= storage_node:
                        load_kg = DEFAULT_LOAD_KG
            
            route_step = RouteStep(
                resource_id=resource.id,
                distance_m=0.0,  # Distance will be calculated by DMAS_ET
                duration_sec=duration,
                load_kg=load_kg,
                is_task_endpoint=is_endpoint,
                due_date=None
            )
            route_steps.append(route_step)
        
        if len(route_steps) == 0:
            return 0.0, 0.0
        
        # Calculate costs using DMAS_ET_silent
        E_j1, TFT_j1 = DMAS_ET_silent(
            route_plan=route_steps,
            global_start_time=auction_start_time,
            agv_id=f"AGV_{agv.agv_id}_J1"
        )
        
        return E_j1, TFT_j1
        
    except Exception as e:
        print(f"[ERROR] Failed to calculate J1 for busy AGV: {e}")
        import traceback
        traceback.print_exc()
        return 0.0, 0.0


class BiddingService:
    """
    Service for calculating AGV bids in the auction process.
    
    Implements Algorithm B (BID_CALCULATION_ET) from the specification.
    """
    
    def __init__(self):
        pass
    
    def calculate_bid_for_agv(
        self, 
        agv, 
        order, 
        E_baseline: float, 
        TFT_baseline: float
    ) -> float:
        """
        Calculate bid for a specific AGV for a specific order.
        
        This is the MAIN implementation of Algorithm B (BID_CALCULATION_ET).
        
        Args:
            agv: AGV model instance
            order: Order model instance
            E_baseline: Baseline energy from AuctioneerService
            TFT_baseline: Baseline TFT from AuctioneerService
            
        Returns:
            float: Final bid value (b_final)
            Returns inf if route is infeasible
            
        Algorithm:
            1. Get current costs (J1) - for idle AGV, J1 = (0, 0)
            2. Create new optimal route plan with order's tasks
            3. Calculate new costs (J2) using DMAS_ET_silent
            4. Calculate marginal costs (J2 - J1)
            5. Normalize by baseline
            6. Calculate MiniSum bid (efficiency)
            7. Calculate MiniMax bid (load balancing)
            8. Combine using epsilon weight
        """
        try:
            print(f"\n[BiddingService] Calculating bid for AGV {agv.agv_id}")
            
            # Determine auction start time
            try:
                auction_start_time = datetime.combine(
                    order.order_date,
                    order.start_time,
                    tzinfo=timezone.utc
                )
            except:
                auction_start_time = datetime.now(timezone.utc)
            
            # Step 1: Get current costs (J1)
            # For IDLE AGV: J1 = (0, 0)
            # For BUSY AGV: J1 = costs to complete current task
            if agv.motion_state == agv.IDLE:
                E_j1 = 0.0
                TFT_j1 = 0.0
                print(f"  AGV state: IDLE")
                print(f"  Current costs (J1): E={E_j1:.3f} kJ, TFT={TFT_j1:.1f}s")
            else:
                print(f"  AGV state: BUSY (motion_state={agv.get_motion_state_display()})")
                print(f"  Calculating J1 (current task completion costs)...")
                E_j1, TFT_j1 = _calculate_j1_for_busy_agv(agv, auction_start_time)
                
                if E_j1 == float('inf') or TFT_j1 == float('inf'):
                    print(f"[ERROR] Cannot calculate J1 for busy AGV")
                    return float('inf')
                
                print(f"  Current costs (J1): E={E_j1:.3f} kJ, TFT={TFT_j1:.1f}s")
            
            # Step 2: Create new route plan with order
            # For IDLE AGV: start from current_node
            # For BUSY AGV: start from completion node (last node in remaining_path)
            print(f"  Creating route plan for new order...")
            new_route_plan = self._create_route_plan_for_order(agv, order)
            
            if new_route_plan is None:
                print(f"[ERROR] Could not create route plan")
                return float('inf')
            
            print(f"  ✓ Route plan created with {len(new_route_plan)} steps")
            
            # Step 3: Calculate new costs (J2) using DMAS_ET_silent
            print(f"  Running DMAS_ET_silent to calculate J2...")
            
            # Start time: use order's start time
            try:
                start_datetime = datetime.combine(
                    order.order_date,
                    order.start_time,
                    tzinfo=timezone.utc
                )
            except:
                # Fallback to current time if order time not available
                start_datetime = datetime.now(timezone.utc)
            
            E_j2, TFT_j2 = DMAS_ET_silent(
                route_plan=new_route_plan,
                global_start_time=start_datetime,
                agv_id=f"AGV_{agv.agv_id}"
            )
            
            if E_j2 == float('inf') or TFT_j2 == float('inf'):
                print(f"[ERROR] Route is infeasible (DMAS_ET returned inf)")
                return float('inf')
            
            print(f"  ✓ New costs (J2): E={E_j2:.3f} kJ, TFT={TFT_j2:.1f}s")
            
            # Step 4: Calculate marginal costs
            E_marginal = E_j2 - E_j1
            TFT_marginal = TFT_j2 - TFT_j1
            
            print(f"  Marginal costs: E={E_marginal:.3f} kJ, TFT={TFT_marginal:.1f}s")
            
            # Step 5: Normalize by baseline
            E_baseline_safe = E_baseline if E_baseline > 0 else FALLBACK_NORM_ENERGY_KJ
            TFT_baseline_safe = TFT_baseline if TFT_baseline > 0 else FALLBACK_NORM_TFT_SEC
            
            E_norm_marginal = E_marginal / E_baseline_safe
            TFT_norm_marginal = TFT_marginal / TFT_baseline_safe
            
            E_norm_total = E_j2 / E_baseline_safe
            TFT_norm_total = TFT_j2 / TFT_baseline_safe
            
            print(f"  Normalized marginal: E={E_norm_marginal:.3f}, TFT={TFT_norm_marginal:.3f}")
            print(f"  Normalized total: E={E_norm_total:.3f}, TFT={TFT_norm_total:.3f}")
            
            # Step 6: Calculate MiniSum bid (efficiency)
            b_ms = (K_ENERGY * E_norm_marginal) + (K_TIME * TFT_norm_marginal)
            
            # Step 7: Calculate MiniMax bid (load balancing)
            b_mm = (K_ENERGY * E_norm_total) + (K_TIME * TFT_norm_total)
            
            # Step 8: Hybrid bid
            b_final = (EPSILON * b_ms) + ((1 - EPSILON) * b_mm)
            
            print(f"  b_ms (MiniSum) = {K_ENERGY}*{E_norm_marginal:.3f} + {K_TIME}*{TFT_norm_marginal:.3f} = {b_ms:.6f}")
            print(f"  b_mm (MiniMax) = {K_ENERGY}*{E_norm_total:.3f} + {K_TIME}*{TFT_norm_total:.3f} = {b_mm:.6f}")
            print(f"  b_final = {EPSILON}*{b_ms:.6f} + {1-EPSILON}*{b_mm:.6f} = {b_final:.6f}")
            
            return b_final
            
        except Exception as e:
            print(f"[ERROR] Bid calculation failed for AGV {agv.agv_id}: {e}")
            import traceback
            traceback.print_exc()
            return float('inf')
    
    def _create_route_plan_for_order(self, agv, order) -> Optional[List[RouteStep]]:
        """
        Create a route plan for an AGV to fulfill an order.
        
        Logic:
        - IDLE AGV: Start from current_node → Storage (pickup) → Workstation (delivery)
        - BUSY AGV: Start from completion_node → Storage (pickup) → Workstation (delivery)
        
        Args:
            agv: AGV model instance
            order: Order model instance
            
        Returns:
            List[RouteStep]: Route steps for DMAS_ET, or None if failed
        """
        try:
            from agv_data.models import ResourceAgent
            from agv_data.services import MapService
            
            # Initialize MapService
            map_service = MapService()
            if map_service._graph is None:
                map_service.load_graph()
            
            # Convert node numbers to names
            def _node_number_to_name(node_num: int) -> Optional[str]:
                """Convert node number to ResourceAgent name."""
                try:
                    # Try CA naming convention
                    ca_name = f"CA-{node_num:02d}"
                    if ResourceAgent.objects.filter(name=ca_name).exists():
                        return ca_name
                    print(f"[WARNING] Node {node_num} does not match CA naming")
                    return None
                except Exception as e:
                    print(f"[ERROR] _node_number_to_name: {e}")
                    return None
            
            # Get resource names from node numbers
            storage_loc = _node_number_to_name(order.storage_node)
            workstation_loc = _node_number_to_name(order.workstation_node)
            
            if storage_loc is None or workstation_loc is None:
                print(f"[ERROR] Failed to map node numbers to names")
                print(f"  storage: {order.storage_node} -> {storage_loc}")
                print(f"  workstation: {order.workstation_node} -> {workstation_loc}")
                return None
            
            # Determine start location
            # IDLE AGV: use current_node
            # BUSY AGV: use completion_node (last node in remaining_path)
            if agv.motion_state == agv.IDLE:
                start_node = agv.current_node
                start_type = "current position"
            else:
                # Get completion node from remaining path
                completion_node = _get_completion_node_from_remaining_path(agv)
                if completion_node is None:
                    print(f"[ERROR] Cannot determine completion node for busy AGV {agv.agv_id}")
                    return None
                start_node = completion_node
                start_type = "completion position (after current task)"
            
            start_loc = _node_number_to_name(start_node) if start_node else None
            
            if start_loc is None:
                print(f"[ERROR] AGV {agv.agv_id} has no valid start location")
                return None
            
            print(f"    Start: {start_loc} ({start_type})")
            print(f"    Route: {start_loc} -> {storage_loc} (pickup) -> {workstation_loc} (delivery)")
            print(f"    Note: Direct route from start, NO detour via parking")
            
            load_kg = DEFAULT_LOAD_KG
            
            # === LEG 1: Start Location -> Storage (EMPTY) ===
            # AGV goes DIRECTLY to pickup point (no parking detour)
            print(f"    Leg 1: {start_loc} -> {storage_loc} (to pickup, EMPTY)")
            route_steps = []
            
            path1 = map_service.get_ideal_path(start_loc, storage_loc)
            
            if path1 is None or len(path1) == 0:
                print(f"[ERROR] No path found: {start_loc} -> {storage_loc}")
                return None
            
            # Minimum reservation duration to avoid 0-duration errors
            MIN_DURATION_SEC = 1.0
            
            for i, step in enumerate(path1):
                # For DMAS_ET, we need resource_id (from database)
                resource = ResourceAgent.objects.get(name=step.node_name)
                
                # Determine if this is a task endpoint
                is_endpoint = (i == len(path1) - 1)  # Last step of leg 1 is pickup point
                
                # Duration: time to traverse from this node to next
                # For last node, use minimum duration
                duration = step.travel_time_sec if step.travel_time_sec > 0 else MIN_DURATION_SEC
                
                route_step = RouteStep(
                    resource_id=resource.id,
                    distance_m=step.distance_m,
                    duration_sec=duration,
                    load_kg=0.0,  # Empty leg
                    is_task_endpoint=is_endpoint,
                    due_date=None
                )
                route_steps.append(route_step)
            
            # === LEG 2: Storage -> Workstation (LOADED) ===
            print(f"    Leg 2: {storage_loc} -> {workstation_loc} (delivery)")
            path2 = map_service.get_ideal_path(storage_loc, workstation_loc)
            
            if path2 is None or len(path2) == 0:
                print(f"[ERROR] No path found: {storage_loc} -> {workstation_loc}")
                return None
            
            for i, step in enumerate(path2):
                resource = ResourceAgent.objects.get(name=step.node_name)
                
                is_endpoint = (i == len(path2) - 1)  # Last step of leg 2 is delivery point
                
                # Duration: time to traverse from this node to next
                # For last node, use minimum duration
                duration = step.travel_time_sec if step.travel_time_sec > 0 else MIN_DURATION_SEC
                
                route_step = RouteStep(
                    resource_id=resource.id,
                    distance_m=step.distance_m,
                    duration_sec=duration,
                    load_kg=load_kg,  # Loaded leg
                    is_task_endpoint=is_endpoint,
                    due_date=None
                )
                route_steps.append(route_step)
            
            return route_steps
            
        except Exception as e:
            print(f"[ERROR] Failed to create route plan: {e}")
            import traceback
            traceback.print_exc()
            return None


def calculate_bid_simple(
    current_energy_kj: float,
    current_tft_sec: float,
    new_route_plan: List[RouteStep],
    start_time: datetime,
    E_baseline: float,
    TFT_baseline: float,
    agv_id: str = "AGV"
) -> float:
    """
    Calculate bid for an AGV using dynamic normalization (simplified version).
    
    This is the core BID_CALCULATION_ET algorithm from the specification.
    
    Args:
        current_energy_kj: Current total energy consumption (J1_E)
        current_tft_sec: Current total flow time (J1_TFT)
        new_route_plan: Route plan including the new task (for J2 calculation)
        start_time: Start time for the new route plan
        E_baseline: Baseline energy for the task
        TFT_baseline: Baseline TFT for the task
        agv_id: AGV identifier for logging
        
    Returns:
        float: Final bid score (b_final)
        Returns inf if route is infeasible
        
    Algorithm:
        1. Get current costs (J1)
        2. Calculate new costs with task (J2) using DMAS-ET
        3. Calculate marginal costs (J2 - J1)
        4. Normalize by baseline
        5. Calculate MiniSum bid (b_ms) from marginal
        6. Calculate MiniMax bid (b_mm) from total
        7. Combine: b_final = epsilon * b_ms + (1 - epsilon) * b_mm
    """
    # Step 1: Current costs (J1) - provided as parameters
    E_j1 = current_energy_kj
    TFT_j1 = current_tft_sec
    
    # Step 2: New costs (J2) with task - run DMAS-ET
    E_j2, TFT_j2 = DMAS_ET_silent(new_route_plan, start_time, agv_id=agv_id)
    
    if E_j2 == float('inf') or TFT_j2 == float('inf'):
        print(f"[BIDDING] {agv_id}: Route infeasible, returning inf")
        return float('inf')
    
    # Step 3: Marginal costs (incremental cost of adding this task)
    E_marginal = E_j2 - E_j1
    TFT_marginal = TFT_j2 - TFT_j1
    
    # Step 4: Normalize (avoid division by zero with fallback)
    E_baseline_safe = E_baseline if E_baseline > 0 else FALLBACK_NORM_ENERGY_KJ
    TFT_baseline_safe = TFT_baseline if TFT_baseline > 0 else FALLBACK_NORM_TFT_SEC
    
    E_norm_marginal = E_marginal / E_baseline_safe
    TFT_norm_marginal = TFT_marginal / TFT_baseline_safe
    
    E_norm_total = E_j2 / E_baseline_safe
    TFT_norm_total = TFT_j2 / TFT_baseline_safe
    
    # Step 5: MiniSum bid (efficiency - prefers AGV with least marginal cost)
    b_ms = (K_ENERGY * E_norm_marginal) + (K_TIME * TFT_norm_marginal)
    
    # Step 6: MiniMax bid (load balancing - prefers AGV with least total load)
    b_mm = (K_ENERGY * E_norm_total) + (K_TIME * TFT_norm_total)
    
    # Step 7: Hybrid bid (balance efficiency and fairness)
    b_final = (EPSILON * b_ms) + ((1 - EPSILON) * b_mm)
    
    # Logging
    print(f"\n[BIDDING] {agv_id} Bid Calculation:")
    print(f"  Current: E={E_j1:.3f} kJ, TFT={TFT_j1:.1f}s")
    print(f"  With task: E={E_j2:.3f} kJ, TFT={TFT_j2:.1f}s")
    print(f"  Marginal: E={E_marginal:.3f} kJ, TFT={TFT_marginal:.1f}s")
    print(f"  Baseline: E={E_baseline:.3f} kJ, TFT={TFT_baseline:.1f}s")
    print(f"  Normalized marginal: E={E_norm_marginal:.3f}, TFT={TFT_norm_marginal:.3f}")
    print(f"  Normalized total: E={E_norm_total:.3f}, TFT={TFT_norm_total:.3f}")
    print(f"  b_ms (MiniSum) = {b_ms:.6f}")
    print(f"  b_mm (MiniMax) = {b_mm:.6f}")
    print(f"  b_final = {EPSILON}*{b_ms:.6f} + {1-EPSILON}*{b_mm:.6f} = {b_final:.6f}")
    
    return b_final


def calculate_bid_detailed(
    current_energy_kj: float,
    current_tft_sec: float,
    new_route_plan: List[RouteStep],
    start_time: datetime,
    E_baseline: float,
    TFT_baseline: float,
    agv_id: str = "AGV"
) -> dict:
    """
    Calculate bid with detailed breakdown (for analysis and debugging).
    
    Returns a dictionary with all intermediate values:
    {
        'bid_final': float,
        'bid_minisum': float,
        'bid_minimax': float,
        'current_energy': float,
        'current_tft': float,
        'new_energy': float,
        'new_tft': float,
        'marginal_energy': float,
        'marginal_tft': float,
        'norm_marginal_energy': float,
        'norm_marginal_tft': float,
        'norm_total_energy': float,
        'norm_total_tft': float,
        'is_feasible': bool
    }
    """
    E_j1 = current_energy_kj
    TFT_j1 = current_tft_sec
    
    E_j2, TFT_j2 = DMAS_ET_silent(new_route_plan, start_time, agv_id=agv_id)
    
    is_feasible = (E_j2 != float('inf') and TFT_j2 != float('inf'))
    
    if not is_feasible:
        return {
            'bid_final': float('inf'),
            'bid_minisum': float('inf'),
            'bid_minimax': float('inf'),
            'is_feasible': False
        }
    
    E_marginal = E_j2 - E_j1
    TFT_marginal = TFT_j2 - TFT_j1
    
    E_baseline_safe = E_baseline if E_baseline > 0 else FALLBACK_NORM_ENERGY_KJ
    TFT_baseline_safe = TFT_baseline if TFT_baseline > 0 else FALLBACK_NORM_TFT_SEC
    
    E_norm_marginal = E_marginal / E_baseline_safe
    TFT_norm_marginal = TFT_marginal / TFT_baseline_safe
    
    E_norm_total = E_j2 / E_baseline_safe
    TFT_norm_total = TFT_j2 / TFT_baseline_safe
    
    b_ms = (K_ENERGY * E_norm_marginal) + (K_TIME * TFT_norm_marginal)
    b_mm = (K_ENERGY * E_norm_total) + (K_TIME * TFT_norm_total)
    b_final = (EPSILON * b_ms) + ((1 - EPSILON) * b_mm)
    
    return {
        'bid_final': b_final,
        'bid_minisum': b_ms,
        'bid_minimax': b_mm,
        'current_energy': E_j1,
        'current_tft': TFT_j1,
        'new_energy': E_j2,
        'new_tft': TFT_j2,
        'marginal_energy': E_marginal,
        'marginal_tft': TFT_marginal,
        'norm_marginal_energy': E_norm_marginal,
        'norm_marginal_tft': TFT_norm_marginal,
        'norm_total_energy': E_norm_total,
        'norm_total_tft': TFT_norm_total,
        'is_feasible': True
    }


# TODO: Implement AGV class integration when ready
# class AGVBidder:
#     """
#     Wrapper class for AGV bidding (future implementation).
#     
#     This will integrate with your existing AGV model to handle:
#     - Current route plan management
#     - Task insertion optimization (TSP)
#     - Bid submission to auctioneer
#     """
#     
#     def __init__(self, agv_model):
#         self.agv = agv_model
#         self.current_energy = 0.0
#         self.current_tft = 0.0
#     
#     def submit_bid(self, new_task, E_baseline, TFT_baseline):
#         """Calculate and submit bid for a new task."""
#         # Get current costs
#         self.current_energy, self.current_tft = self.agv.get_current_costs()
#         
#         # Create new optimal plan (TODO: implement TSP)
#         new_route_plan = self._create_optimal_plan(new_task)
#         
#         # Calculate bid
#         bid = calculate_bid_simple(
#             current_energy_kj=self.current_energy,
#             current_tft_sec=self.current_tft,
#             new_route_plan=new_route_plan,
#             start_time=self.agv.start_time,
#             E_baseline=E_baseline,
#             TFT_baseline=TFT_baseline,
#             agv_id=self.agv.agv_id
#         )
#         
#         return bid


if __name__ == "__main__":
    # Example usage
    from datetime import datetime, timezone, timedelta
    
    print("="*60)
    print("BIDDING SERVICE - BID CALCULATION TEST")
    print("="*60)
    
    # Test scenario: AGV currently idle, receives new task
    print("\nScenario: Idle AGV receives task")
    
    # Current state (idle)
    current_E = 0.0
    current_TFT = 0.0
    
    # Baseline costs (from auctioneer)
    E_baseline = 67.5  # kJ (from auctioneer calculation)
    TFT_baseline = 150.0  # seconds
    
    # New route plan (2 segments: depot->pickup, pickup->delivery)
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    
    new_route = [
        # Segment 1: Depot to Pickup (empty, 100m, 60s)
        RouteStep(
            resource_id=1,
            distance_m=100.0,
            duration_sec=60.0,
            load_kg=0.0,
            is_task_endpoint=False
        ),
        # Segment 2: Pickup location
        RouteStep(
            resource_id=2,
            distance_m=10.0,
            duration_sec=20.0,
            load_kg=200.0,
            is_task_endpoint=True
        ),
        # Segment 3: Travel to Delivery (loaded, 150m, 90s)
        RouteStep(
            resource_id=3,
            distance_m=150.0,
            duration_sec=90.0,
            load_kg=200.0,
            is_task_endpoint=False
        ),
        # Segment 4: Delivery location
        RouteStep(
            resource_id=4,
            distance_m=10.0,
            duration_sec=20.0,
            load_kg=0.0,
            is_task_endpoint=True
        )
    ]
    
    # Calculate bid
    bid = calculate_bid_simple(
        current_energy_kj=current_E,
        current_tft_sec=current_TFT,
        new_route_plan=new_route,
        start_time=start_time,
        E_baseline=E_baseline,
        TFT_baseline=TFT_baseline,
        agv_id="TEST_AGV_1"
    )
    
    print(f"\n{'='*60}")
    print(f"FINAL BID: {bid:.6f}")
    print(f"{'='*60}")
    
    # Test detailed version
    print("\n\nTest 2: Detailed bid breakdown")
    bid_details = calculate_bid_detailed(
        current_energy_kj=current_E,
        current_tft_sec=current_TFT,
        new_route_plan=new_route,
        start_time=start_time,
        E_baseline=E_baseline,
        TFT_baseline=TFT_baseline,
        agv_id="TEST_AGV_2"
    )
    
    print("\nDetailed Breakdown:")
    for key, value in bid_details.items():
        if isinstance(value, float) and value != float('inf'):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    print("\nNote: These tests require Django server running.")
    print("If API calls fail, tests will return inf.")
