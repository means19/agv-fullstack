"""
AGV Agent Logic - Exploring Ant (DMAS-ET)

This module provides backward-compatible wrappers for the refactored Exploring Ant algorithm.
The actual implementation is now in the exploring_ants package with clean architecture.

For new code, prefer importing directly from exploring_ants package:
    from agv_data.exploring_ants import ExploringAntService, RouteStep

Reference: docs/exploring-ants/agv-agent-exploring-ant.md
"""

from datetime import datetime
from typing import List, Tuple

# Import from refactored package
from .exploring_ants import (
    RouteStep,
    ExploringAntService,
    EnergyCalculationService,
    ReservationTableClient,
    DEFAULT_CONFIG,
    # Backward compatibility constants
    K_ENERGY,
    K_TIME,
    RESERVATION_API_URL,
    IDLE_POWER,
)

# Import deprecated constants from agv_agent_constants for backward compatibility
from .agv_agent_constants import C_BASE, C_LOAD_COEFF, P_IDLE

# Create default service instances for backward compatibility
_default_energy_service = EnergyCalculationService()
_default_reservation_client = ReservationTableClient()
_default_exploring_ant_service = ExploringAntService(verbose=True)
_default_exploring_ant_service_silent = ExploringAntService(verbose=False)


# Backward compatibility functions
def _calculate_energy_travel(distance_m: float, load_kg: float) -> float:
    """
    Calculate energy consumption for traveling a certain distance with a load.
    
    [DEPRECATED] This is a backward compatibility wrapper.
    Use EnergyCalculationService.calculate_travel_energy() instead.
    
    Args:
        distance_m: Distance to travel in meters
        load_kg: Load weight in kilograms
        
    Returns:
        Energy consumption in kilojoules (kJ)
    """
    return _default_energy_service.calculate_travel_energy(distance_m, load_kg)


def _calculate_energy_wait(delay_sec: float) -> float:
    """
    Calculate energy consumption while waiting (idle).
    
    [DEPRECATED] This is a backward compatibility wrapper.
    Use EnergyCalculationService.calculate_wait_energy() instead.
    
    Args:
        delay_sec: Delay time in seconds
        
    Returns:
        Energy consumption in kilojoules (kJ)
    """
    return _default_energy_service.calculate_wait_energy(delay_sec)


def _query_slot_api(
    resource_id: int,
    desired_start: datetime,
    duration_sec: float,
    api_base_url: str = RESERVATION_API_URL
):
    """
    Call the Reservation Table API to query for the earliest available slot.
    
    [DEPRECATED] This is a backward compatibility wrapper.
    Use ReservationTableClient.query_slot() instead.
    
    Args:
        resource_id: ID of the resource (CA or LSA)
        desired_start: Desired start time for the reservation
        duration_sec: Duration of the reservation in seconds
        api_base_url: Base URL of the Reservation API (ignored, uses config)
        
    Returns:
        API response dict with 'earliest_available_start' or None if API fails
    """
    return _default_reservation_client.query_slot_safe(
        resource_id, desired_start, duration_sec, verbose=True
    )


def DMAS_ET(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> Tuple[float, float]:
    """
    Exploring Ant (DMAS-ET) - Simulates an AGV's journey and calculates total cost.
    
    [REFACTORED] This function now delegates to ExploringAntService for cleaner architecture.
    
    This function:
    1. Iterates through each step in the route plan
    2. Queries the Reservation Table API for earliest available slot
    3. Calculates travel energy and wait energy
    4. Tracks Total Flow Time (TFT)
    5. Returns RAW costs (E, TFT) - normalization done by bidding layer
    
    Args:
        route_plan: List of RouteStep objects representing the planned route
        global_start_time: Initial start time for the journey
        agv_id: Identifier for this exploring ant (for logging)
        
    Returns:
        Tuple[float, float]: (total_energy_kj, total_tft_sec)
        Returns (float('inf'), float('inf')) if:
        - Route plan is empty
        - Any API call fails
        - Any validation fails
        
    Note:
        TFT (Total Flow Time) replaced SOT (Sum of Tardiness) as the time metric.
        TFT is always positive and measures overall performance.
        
    Migration:
        For new code, use ExploringAntService directly:
        >>> from agv_data.exploring_ants import ExploringAntService
        >>> service = ExploringAntService(verbose=True)
        >>> energy, tft = service.explore(route_plan, global_start_time, agv_id)
    """
    return _default_exploring_ant_service.explore(route_plan, global_start_time, agv_id)


def DMAS_ET_silent(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> Tuple[float, float]:
    """
    Silent version of DMAS_ET (no console output) for performance and bidding.
    
    [REFACTORED] This function now delegates to ExploringAntService in silent mode.
    
    Returns RAW costs (energy, TFT) without applying K_ENERGY/K_TIME weights.
    This allows the bidding layer to apply dynamic normalization.
    
    Args:
        route_plan: List of RouteStep objects
        global_start_time: Start time for the journey
        agv_id: Identifier for logging
        
    Returns:
        Tuple[float, float]: (total_energy_kj, total_tft_sec)
        Returns (inf, inf) if route is invalid or API fails
        
    Note:
        TFT (Total Flow Time) = time from start to completion of last task endpoint
        
    Migration:
        For new code, use ExploringAntService directly:
        >>> from agv_data.exploring_ants import ExploringAntService
        >>> service = ExploringAntService(verbose=False)
        >>> energy, tft = service.explore_silent(route_plan, global_start_time, agv_id)
    """
    return _default_exploring_ant_service_silent.explore(route_plan, global_start_time, agv_id)
