"""
Exploring Ant Service (DMAS-ET)

This module implements the main Exploring Ant algorithm for the Delegate Multi-Agent System (D-MAS).
The Exploring Ant simulates an AGV's journey through a route plan, querying the Reservation Table
for each resource, and calculates the total cost based on energy consumption and Total Flow Time (TFT).

Architecture:
    This service uses dependency injection to compose smaller specialized services:
    - EnergyCalculationService: Calculates travel and wait energy
    - ReservationTableClient: Queries the Reservation Table API
    
    The service provides two execution modes via Strategy pattern:
    - Verbose: Detailed console output for debugging
    - Silent: No output, optimized for performance
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod

from ..models import RouteStep
from ..clients import ReservationTableClient
from .energy_calculation import EnergyCalculationService
from ..config import ExploringAntConfig, DEFAULT_CONFIG


class OutputStrategy(ABC):
    """Abstract base class for output strategies."""
    
    @abstractmethod
    def log_start(self, agv_id: str, start_time: datetime, num_steps: int):
        """Log exploration start."""
        pass
    
    @abstractmethod
    def log_step(self, step_idx: int, step: RouteStep, desired_start: datetime, 
                 earliest_start: datetime, delay_sec: float, 
                 wait_energy: float, travel_energy: float, finish_time: datetime):
        """Log step execution."""
        pass
    
    @abstractmethod
    def log_task_endpoint(self, flow_time: float, due_date: Optional[datetime], finish_time: datetime):
        """Log task endpoint completion."""
        pass
    
    @abstractmethod
    def log_completion(self, agv_id: str, total_energy: float, total_tft: float):
        """Log exploration completion."""
        pass
    
    @abstractmethod
    def log_error(self, agv_id: str, message: str):
        """Log error."""
        pass


class VerboseOutput(OutputStrategy):
    """Verbose output strategy with detailed console logging."""
    
    def log_start(self, agv_id: str, start_time: datetime, num_steps: int):
        print(f"\n[DMAS-ET] {agv_id} starting exploration at {start_time}")
        print(f"[DMAS-ET] Route has {num_steps} steps")
    
    def log_step(self, step_idx: int, step: RouteStep, desired_start: datetime,
                 earliest_start: datetime, delay_sec: float,
                 wait_energy: float, travel_energy: float, finish_time: datetime):
        print(f"\n--- Step {step_idx + 1} ---")
        print(f"Resource ID: {step.resource_id}")
        print(f"Distance: {step.distance_m}m, Duration: {step.duration_sec}s")
        print(f"Load: {step.load_kg}kg, Task endpoint: {step.is_task_endpoint}")
        print(f"Desired start: {desired_start}")
        print(f"Earliest available: {earliest_start}")
        
        if delay_sec > 0:
            print(f"Delay: {delay_sec}s")
            print(f"Wait energy: {wait_energy:.6f} kJ")
        else:
            print("No delay")
        
        print(f"Travel energy: {travel_energy:.6f} kJ")
        print(f"Finish time: {finish_time}")
    
    def log_task_endpoint(self, flow_time: float, due_date: Optional[datetime], finish_time: datetime):
        print(f"[TASK ENDPOINT] Flow time: {flow_time:.2f}s")
        if due_date is not None:
            if finish_time > due_date:
                late_by = (finish_time - due_date).total_seconds()
                print(f"[LATE] by {late_by}s (due: {due_date})")
            else:
                print(f"[ON TIME] (due: {due_date})")
    
    def log_completion(self, agv_id: str, total_energy: float, total_tft: float):
        print(f"\n{'='*60}")
        print(f"[DMAS-ET] {agv_id} Exploration Complete")
        print(f"{'='*60}")
        print(f"Total Energy: {total_energy:.6f} kJ")
        print(f"Total Flow Time (TFT): {total_tft:.2f} seconds")
        print(f"\n⚠️  NOTE: Raw costs returned (E, TFT)")
        print(f"    Normalization & J calculation done by bidding layer")
        print(f"{'='*60}\n")
    
    def log_error(self, agv_id: str, message: str):
        print(f"[ERROR] {agv_id}: {message}")


class SilentOutput(OutputStrategy):
    """Silent output strategy with no console output."""
    
    def log_start(self, agv_id: str, start_time: datetime, num_steps: int):
        pass
    
    def log_step(self, step_idx: int, step: RouteStep, desired_start: datetime,
                 earliest_start: datetime, delay_sec: float,
                 wait_energy: float, travel_energy: float, finish_time: datetime):
        pass
    
    def log_task_endpoint(self, flow_time: float, due_date: Optional[datetime], finish_time: datetime):
        pass
    
    def log_completion(self, agv_id: str, total_energy: float, total_tft: float):
        pass
    
    def log_error(self, agv_id: str, message: str):
        pass


class ExploringAntService:
    """
    Main service for executing the Exploring Ant (DMAS-ET) algorithm.
    
    This service simulates an AGV's journey through a route plan and calculates
    the total cost in terms of energy consumption and Total Flow Time (TFT).
    
    The service uses dependency injection to compose smaller services:
    - EnergyCalculationService: Energy calculations
    - ReservationTableClient: API queries
    - OutputStrategy: Logging behavior (verbose/silent)
    
    Attributes:
        energy_service: Service for energy calculations
        reservation_client: Client for Reservation Table API
        config: Exploring Ant configuration
        output_strategy: Output strategy (verbose or silent)
        
    Example:
        >>> from datetime import datetime, timezone
        >>> service = ExploringAntService()
        >>> route = [
        ...     RouteStep(resource_id=1, distance_m=50.0, duration_sec=30.0, 
        ...               load_kg=0.0, is_task_endpoint=False),
        ...     RouteStep(resource_id=2, distance_m=100.0, duration_sec=60.0,
        ...               load_kg=100.0, is_task_endpoint=True)
        ... ]
        >>> energy, tft = service.explore(route, datetime.now(timezone.utc))
        >>> print(f"Energy: {energy} kJ, TFT: {tft}s")
    """
    
    def __init__(
        self,
        energy_service: EnergyCalculationService = None,
        reservation_client: ReservationTableClient = None,
        config: ExploringAntConfig = None,
        verbose: bool = True
    ):
        """
        Initialize the Exploring Ant service.
        
        Args:
            energy_service: Energy calculation service (uses default if None)
            reservation_client: Reservation Table client (uses default if None)
            config: Configuration (uses DEFAULT_CONFIG if None)
            verbose: If True, use verbose output; if False, use silent output
        """
        self.config = config or DEFAULT_CONFIG
        self.energy_service = energy_service or EnergyCalculationService(self.config.energy)
        self.reservation_client = reservation_client or ReservationTableClient(self.config.api)
        self.output_strategy = VerboseOutput() if verbose else SilentOutput()
    
    def explore(
        self,
        route_plan: List[RouteStep],
        global_start_time: datetime,
        agv_id: str = "exploring_ant"
    ) -> Tuple[float, float]:
        """
        Execute the Exploring Ant algorithm (DMAS-ET).
        
        This method:
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
        # Validate route plan
        if not route_plan:
            self.output_strategy.log_error(agv_id, "Route plan is empty")
            return (float('inf'), float('inf'))
        
        # Initialize tracking variables
        current_time = global_start_time
        total_energy_kj = 0.0
        total_tft_sec = 0.0
        
        # Log exploration start
        self.output_strategy.log_start(agv_id, current_time, len(route_plan))
        
        # Process each step in the route
        for step_idx, step in enumerate(route_plan):
            # Query Reservation Table for earliest available slot
            api_response = self.reservation_client.query_slot_safe(
                resource_id=step.resource_id,
                desired_start=current_time,
                duration_sec=step.duration_sec,
                verbose=isinstance(self.output_strategy, VerboseOutput)
            )
            
            if api_response is None:
                self.output_strategy.log_error(
                    agv_id, 
                    f"API call failed at step {step_idx + 1}"
                )
                return (float('inf'), float('inf'))
            
            # Parse earliest available start time
            earliest_start = self.reservation_client.parse_earliest_start(api_response)
            if earliest_start is None:
                self.output_strategy.log_error(
                    agv_id,
                    f"Invalid API response at step {step_idx + 1}"
                )
                return (float('inf'), float('inf'))
            
            # Calculate delay and wait energy
            delay_sec = 0.0
            wait_energy = 0.0
            if earliest_start > current_time:
                delay_sec = (earliest_start - current_time).total_seconds()
                wait_energy = self.energy_service.calculate_wait_energy(delay_sec)
                total_energy_kj += wait_energy
                current_time = earliest_start
            
            # Calculate travel energy
            travel_energy = self.energy_service.calculate_travel_energy(
                step.distance_m, 
                step.load_kg
            )
            total_energy_kj += travel_energy
            
            # Update current time after completing this step
            finish_time = current_time + timedelta(seconds=step.duration_sec)
            current_time = finish_time
            
            # Log step execution
            self.output_strategy.log_step(
                step_idx, step, 
                earliest_start - timedelta(seconds=delay_sec) if delay_sec > 0 else current_time,
                earliest_start, delay_sec, wait_energy, travel_energy, finish_time
            )
            
            # Track TFT for task endpoints
            if step.is_task_endpoint:
                flow_time = (finish_time - global_start_time).total_seconds()
                total_tft_sec = flow_time
                self.output_strategy.log_task_endpoint(
                    flow_time, step.due_date, finish_time
                )
        
        # Log completion
        self.output_strategy.log_completion(agv_id, total_energy_kj, total_tft_sec)
        
        # Return RAW costs (normalization & J calculation done by bidding layer)
        return (total_energy_kj, total_tft_sec)
    
    def explore_silent(
        self,
        route_plan: List[RouteStep],
        global_start_time: datetime,
        agv_id: str = "exploring_ant"
    ) -> Tuple[float, float]:
        """
        Execute Exploring Ant in silent mode (no output).
        
        This is a convenience method that temporarily switches to silent output,
        executes the exploration, and returns the results.
        
        Args:
            route_plan: List of RouteStep objects
            global_start_time: Start time for the journey
            agv_id: Identifier for logging
            
        Returns:
            Tuple[float, float]: (total_energy_kj, total_tft_sec)
            Returns (inf, inf) if route is invalid or API fails
        """
        # Save current strategy
        original_strategy = self.output_strategy
        
        # Switch to silent mode
        self.output_strategy = SilentOutput()
        
        try:
            return self.explore(route_plan, global_start_time, agv_id)
        finally:
            # Restore original strategy
            self.output_strategy = original_strategy
