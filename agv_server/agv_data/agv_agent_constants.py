"""
Constants for AGV Agent Logic (Exploring Ant - DMAS-ET)

[UPDATED TO PHYSICS-BASED MODEL]
This file now re-exports constants from the new exploring_ants.config package.
The energy model has been upgraded from simple linear coefficients to physics-based calculations.

⚠️ DEPRECATION WARNING:
    C_BASE and C_LOAD_COEFF are deprecated (old linear model)
    Use physics-based parameters instead:
        - MASS_AGV, FRICTION_COEFF, GRAVITY
        - MOTOR_EFFICIENCY, MAX_VELOCITY, ACCELERATION
        - IDLE_POWER

For new code, prefer importing from the config package:
    from agv_data.exploring_ants.config import ExploringAntConfig, DEFAULT_CONFIG

Migration example:
    Old: energy = (C_BASE + C_LOAD_COEFF * load) * distance
    New: service = EnergyCalculationService()
         energy = service.calculate_travel_energy(distance, load)

Reference: docs/exploring-ants/architecture.md (Physics-Based Energy Model section)
"""

# Import new physics-based constants
from .exploring_ants.config import (
    K_ENERGY,
    K_TIME,
    EPSILON,
    FALLBACK_NORM_ENERGY_KJ,
    FALLBACK_NORM_TFT_SEC,
    RESERVATION_API_URL,
    DEFAULT_CONFIG,
    # New physics parameters
    MASS_AGV,
    FRICTION_COEFF,
    GRAVITY,
    MOTOR_EFFICIENCY,
    MAX_VELOCITY,
    ACCELERATION,
    IDLE_POWER,
)

# Backward compatibility: Provide pseudo-constants for old linear model
# These are deprecated and should not be used in new code
# Approximate values based on physics model for typical scenarios
C_BASE = 0.05  # Deprecated - use physics-based model
C_LOAD_COEFF = 0.002  # Deprecated - use physics-based model
P_IDLE = IDLE_POWER  # Renamed to IDLE_POWER in new model

# Re-export everything for backward compatibility
__all__ = [
    'K_ENERGY',
    'K_TIME',
    'EPSILON',
    'FALLBACK_NORM_ENERGY_KJ',
    'FALLBACK_NORM_TFT_SEC',
    'RESERVATION_API_URL',
    'DEFAULT_CONFIG',
    # Deprecated (backward compatibility only)
    'C_BASE',
    'C_LOAD_COEFF',
    'P_IDLE',
    # New physics parameters
    'MASS_AGV',
    'FRICTION_COEFF',
    'GRAVITY',
    'MOTOR_EFFICIENCY',
    'MAX_VELOCITY',
    'ACCELERATION',
    'IDLE_POWER',
]
