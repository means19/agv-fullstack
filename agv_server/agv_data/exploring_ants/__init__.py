"""
Exploring Ants Package

This package implements the Exploring Ant algorithm (DMAS-ET) for the 
Delegate Multi-Agent System with Energy and Time objectives.

Architecture:
    - models/: Data models (RouteStep)
    - services/: Business logic (ExploringAntService, EnergyCalculationService)
    - clients/: External API clients (ReservationTableClient)
    - config/: Configuration classes (ExploringAntConfig)

Usage:
    >>> from agv_data.exploring_ants import ExploringAntService, RouteStep
    >>> from datetime import datetime, timezone
    >>> 
    >>> # Create service
    >>> service = ExploringAntService()
    >>> 
    >>> # Create route plan
    >>> route = [
    ...     RouteStep(resource_id=1, distance_m=50.0, duration_sec=30.0, 
    ...               load_kg=0.0, is_task_endpoint=False),
    ...     RouteStep(resource_id=2, distance_m=100.0, duration_sec=60.0,
    ...               load_kg=100.0, is_task_endpoint=True)
    ... ]
    >>> 
    >>> # Explore route
    >>> energy, tft = service.explore(route, datetime.now(timezone.utc))
    >>> print(f"Energy: {energy} kJ, TFT: {tft}s")
"""

# Core exports
from .models import RouteStep
from .services import (
    ExploringAntService,
    EnergyCalculationService,
    OutputStrategy,
    VerboseOutput,
    SilentOutput
)
from .clients import (
    ReservationTableClient,
    ReservationTableAPIError
)
from .config import (
    EnergyConfig,
    CostWeights,
    NormalizationConfig,
    APIConfig,
    ExploringAntConfig,
    DEFAULT_CONFIG,
    # Backward compatibility constants
    K_ENERGY,
    K_TIME,
    EPSILON,
    FALLBACK_NORM_ENERGY_KJ,
    FALLBACK_NORM_TFT_SEC,
    RESERVATION_API_URL,
    # Physics-based parameters
    MASS_AGV,
    FRICTION_COEFF,
    GRAVITY,
    MOTOR_EFFICIENCY,
    MAX_VELOCITY,
    ACCELERATION,
    IDLE_POWER,
)

__all__ = [
    # Models
    'RouteStep',
    
    # Services
    'ExploringAntService',
    'EnergyCalculationService',
    'OutputStrategy',
    'VerboseOutput',
    'SilentOutput',
    
    # Clients
    'ReservationTableClient',
    'ReservationTableAPIError',
    
    # Config
    'EnergyConfig',
    'CostWeights',
    'NormalizationConfig',
    'APIConfig',
    'ExploringAntConfig',
    'DEFAULT_CONFIG',
    
    # Backward compatibility constants
    'K_ENERGY',
    'K_TIME',
    'EPSILON',
    'FALLBACK_NORM_ENERGY_KJ',
    'FALLBACK_NORM_TFT_SEC',
    'RESERVATION_API_URL',
    # Physics-based parameters
    'MASS_AGV',
    'FRICTION_COEFF',
    'GRAVITY',
    'MOTOR_EFFICIENCY',
    'MAX_VELOCITY',
    'ACCELERATION',
    'IDLE_POWER',
]

__version__ = '2.0.0'
