"""
Bidding Service - Calculate AGV Bids with Dynamic Normalization

This module implements the bidding logic for AGV agents in the SSI-DMAS-ET system.
It uses dynamic baseline normalization to ensure fair comparison of bids across different tasks.

Key concepts:
- Marginal cost: Additional cost for accepting a new task
- Normalization: Divide by baseline to get scale-free efficiency score
- Hybrid objective: Balance between MiniSum (efficiency) and MiniMax (load balancing)
"""

from typing import Tuple, List
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
    FALLBACK_NORM_TFT_SEC
)
from datetime import datetime


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
