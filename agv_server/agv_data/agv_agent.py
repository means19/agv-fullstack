"""
AGV Agent Logic - Exploring Ant (DMAS-ET)

This module implements the Exploring Ant algorithm for the Delegate Multi-Agent System (D-MAS).
The Exploring Ant simulates an AGV's journey through a route plan, querying the Reservation Table
for each resource, and calculates the total cost based on energy consumption and tardiness.

Reference: agv_agent_logic.md
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
from .agv_agent_constants import (
    K_ENERGY,
    K_TIME,
    C_BASE,
    C_LOAD_COEFF,
    P_IDLE,
    RESERVATION_API_URL
)


class RouteStep:
    """
    Represents one step in an AGV's route plan.
    """
    def __init__(
        self,
        resource_id: int,
        distance_m: float,
        duration_sec: float,
        load_kg: float,
        is_task_endpoint: bool,
        due_date: Optional[datetime] = None
    ):
        self.resource_id = resource_id
        self.distance_m = distance_m
        self.duration_sec = duration_sec
        self.load_kg = load_kg
        self.is_task_endpoint = is_task_endpoint
        self.due_date = due_date
    
    def __repr__(self):
        return (
            f"RouteStep(resource_id={self.resource_id}, "
            f"distance_m={self.distance_m}, duration_sec={self.duration_sec}, "
            f"load_kg={self.load_kg}, is_task_endpoint={self.is_task_endpoint})"
        )


def _calculate_energy_travel(distance_m: float, load_kg: float) -> float:
    """
    Calculate energy consumption for traveling a certain distance with a load.
    
    Formula: E_travel = (C_BASE + C_LOAD_COEFF * load_kg) * distance_m
    
    Args:
        distance_m: Distance to travel in meters
        load_kg: Load weight in kilograms
        
    Returns:
        Energy consumption in kilojoules (kJ)
    """
    return (C_BASE + C_LOAD_COEFF * load_kg) * distance_m


def _calculate_energy_wait(delay_sec: float) -> float:
    """
    Calculate energy consumption while waiting (idle).
    
    Formula: E_wait = P_IDLE * delay_sec / 1000
    
    Args:
        delay_sec: Delay time in seconds
        
    Returns:
        Energy consumption in kilojoules (kJ)
        
    Note:
        P_IDLE is in Watts (W = J/s)
        0.1 W * 60 s = 6 J = 0.006 kJ
    """
    return P_IDLE * delay_sec / 1000.0


def _query_slot_api(
    resource_id: int,
    desired_start: datetime,
    duration_sec: float,
    api_base_url: str = RESERVATION_API_URL
) -> Optional[Dict]:
    """
    Call the Reservation Table API to query for the earliest available slot.
    
    Args:
        resource_id: ID of the resource (CA or LSA)
        desired_start: Desired start time for the reservation
        duration_sec: Duration of the reservation in seconds
        api_base_url: Base URL of the Reservation API
        
    Returns:
        API response dict with 'earliest_available_start' or None if API fails
    """
    url = f"{api_base_url}/resource/{resource_id}/query_slot/"
    
    payload = {
        "request_start_time": desired_start.isoformat(),
        "duration_seconds": int(duration_sec)
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] API call failed for resource {resource_id}: {e}")
        return None


def DMAS_ET(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> Tuple[float, float]:
    """
    Exploring Ant (DMAS-ET) - Simulates an AGV's journey and calculates total cost.
    
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
    """
    if not route_plan:
        print(f"[ERROR] {agv_id}: Route plan is empty")
        return (float('inf'), float('inf'))
    
    # Initialize tracking variables
    current_time = global_start_time
    total_energy_kj = 0.0
    total_tft_sec = 0.0
    
    print(f"\n[DMAS-ET] {agv_id} starting exploration at {current_time}")
    print(f"[DMAS-ET] Route has {len(route_plan)} steps")
    
    for step_idx, step in enumerate(route_plan):
        print(f"\n--- Step {step_idx + 1}/{len(route_plan)} ---")
        print(f"Resource ID: {step.resource_id}")
        print(f"Distance: {step.distance_m}m, Duration: {step.duration_sec}s")
        print(f"Load: {step.load_kg}kg, Task endpoint: {step.is_task_endpoint}")
        
        # Query the Reservation Table for earliest available slot
        api_response = _query_slot_api(
            resource_id=step.resource_id,
            desired_start=current_time,
            duration_sec=step.duration_sec
        )
        
        if api_response is None:
            print(f"[ERROR] {agv_id}: API call failed at step {step_idx + 1}")
            return (float('inf'), float('inf'))
        
        # Parse the earliest available start time from API
        earliest_start_str = api_response.get('earliest_available_start')
        if not earliest_start_str:
            print(f"[ERROR] {agv_id}: Invalid API response at step {step_idx + 1}")
            return (float('inf'), float('inf'))
        
        earliest_start = datetime.fromisoformat(earliest_start_str)
        print(f"Desired start: {current_time}")
        print(f"Earliest available: {earliest_start}")
        
        # Calculate delay (if earliest start is later than current time)
        if earliest_start > current_time:
            delay_sec = (earliest_start - current_time).total_seconds()
            print(f"Delay: {delay_sec}s")
            
            # Calculate wait energy
            wait_energy = _calculate_energy_wait(delay_sec)
            total_energy_kj += wait_energy
            print(f"Wait energy: {wait_energy:.6f} kJ")
            
            # Update current time to earliest available
            current_time = earliest_start
        else:
            delay_sec = 0
            print("No delay")
        
        # Calculate travel energy
        travel_energy = _calculate_energy_travel(step.distance_m, step.load_kg)
        total_energy_kj += travel_energy
        print(f"Travel energy: {travel_energy:.6f} kJ")
        
        # Update current time after completing this step
        finish_time = current_time + timedelta(seconds=step.duration_sec)
        current_time = finish_time
        print(f"Finish time: {finish_time}")
        
        # Track TFT for task endpoints
        if step.is_task_endpoint:
            flow_time = (finish_time - global_start_time).total_seconds()
            total_tft_sec = flow_time
            print(f"[TASK ENDPOINT] Flow time: {flow_time:.2f}s")
            if step.due_date is not None:
                if finish_time > step.due_date:
                    late_by = (finish_time - step.due_date).total_seconds()
                    print(f"[LATE] by {late_by}s (due: {step.due_date})")
                else:
                    print(f"[ON TIME] (due: {step.due_date})")
    
    # Print exploration results
    print(f"\n{'='*60}")
    print(f"[DMAS-ET] {agv_id} Exploration Complete")
    print(f"{'='*60}")
    print(f"Total Energy: {total_energy_kj:.6f} kJ")
    print(f"Total Flow Time (TFT): {total_tft_sec:.2f} seconds")
    print(f"\n⚠️  NOTE: Raw costs returned (E, TFT)")
    print(f"    Normalization & J calculation done by bidding layer")
    print(f"{'='*60}\n")
    
    # Return RAW costs (không tính J ở đây)
    # Việc chuẩn hóa và áp dụng K_ENERGY/K_TIME
    # sẽ do hàm BID_CALCULATION_ET bên ngoài xử lý
    return (total_energy_kj, total_tft_sec)


def DMAS_ET_silent(
    route_plan: List[RouteStep],
    global_start_time: datetime,
    agv_id: str = "exploring_ant"
) -> Tuple[float, float]:
    """
    Silent version of DMAS_ET (no console output) for performance and bidding.
    
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
    """
    if not route_plan:
        return float('inf'), float('inf')
    
    current_time = global_start_time
    total_energy_kj = 0.0
    total_tft_sec = 0.0
    
    for step in route_plan:
        try:
            api_response = _query_slot_api(
                resource_id=step.resource_id,
                desired_start=current_time,
                duration_sec=step.duration_sec
            )
            
            if api_response is None:
                return float('inf'), float('inf')
            
            earliest_start_str = api_response.get('earliest_available_start')
            if not earliest_start_str:
                return float('inf'), float('inf')
            
            earliest_start = datetime.fromisoformat(earliest_start_str)
            
            if earliest_start > current_time:
                delay_sec = (earliest_start - current_time).total_seconds()
                wait_energy = _calculate_energy_wait(delay_sec)
                total_energy_kj += wait_energy
                current_time = earliest_start
            
            travel_energy = _calculate_energy_travel(step.distance_m, step.load_kg)
            total_energy_kj += travel_energy
            
            finish_time = current_time + timedelta(seconds=step.duration_sec)
            current_time = finish_time
            
            # TFT: track flow time for task endpoints
            if step.is_task_endpoint:
                flow_time_for_this_task = (current_time - global_start_time).total_seconds()
                total_tft_sec = flow_time_for_this_task
        
        except Exception:
            return float('inf'), float('inf')
    
    return total_energy_kj, total_tft_sec
