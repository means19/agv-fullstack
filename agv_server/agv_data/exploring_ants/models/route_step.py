"""
Route Step Model for Exploring Ant

This module defines the RouteStep dataclass representing one step in an AGV's route plan.
Each step contains information about the resource, distance, duration, load, and whether
it's a task endpoint.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class RouteStep:
    """
    Represents one step in an AGV's route plan.
    
    Each RouteStep contains all necessary information for the Exploring Ant
    to simulate traversing that step: which resource (CA/LSA) it uses,
    how far it travels, how long it takes, what load it's carrying,
    and whether this step marks the completion of a task.
    
    Attributes:
        resource_id: ID of the ResourceAgent (CA or LSA) for this step
        distance_m: Distance to travel in meters
        duration_sec: Duration to occupy the resource in seconds
        load_kg: Load weight carried during this step in kilograms
        is_task_endpoint: True if this step completes a task (pickup/delivery)
        due_date: Optional deadline for this step (for tardiness tracking)
    
    Example:
        >>> step = RouteStep(
        ...     resource_id=5,
        ...     distance_m=50.0,
        ...     duration_sec=30.0,
        ...     load_kg=100.0,
        ...     is_task_endpoint=True,
        ...     due_date=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        ... )
        >>> print(step)
        RouteStep(resource_id=5, distance_m=50.0, duration_sec=30.0, 
                  load_kg=100.0, is_task_endpoint=True)
    """
    
    resource_id: int
    distance_m: float
    duration_sec: float
    load_kg: float
    is_task_endpoint: bool
    due_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate RouteStep attributes after initialization."""
        if self.resource_id <= 0:
            raise ValueError(f"resource_id must be positive, got {self.resource_id}")
        if self.distance_m < 0:
            raise ValueError(f"distance_m cannot be negative, got {self.distance_m}")
        if self.duration_sec <= 0:
            raise ValueError(f"duration_sec must be positive, got {self.duration_sec}")
        if self.load_kg < 0:
            raise ValueError(f"load_kg cannot be negative, got {self.load_kg}")
    
    def is_loaded(self) -> bool:
        """
        Check if this step involves carrying a load.
        
        Returns:
            bool: True if load_kg > 0, False otherwise
        """
        return self.load_kg > 0
    
    def is_empty(self) -> bool:
        """
        Check if this step is empty (no load).
        
        Returns:
            bool: True if load_kg == 0, False otherwise
        """
        return self.load_kg == 0
