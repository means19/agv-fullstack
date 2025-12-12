"""
Config package for Exploring Ant

Exports configuration classes for the algorithm.
"""

from .config import (
    EnergyConfig,
    CostWeights,
    NormalizationConfig,
    APIConfig,
    ExploringAntConfig,
    DEFAULT_CONFIG,
    # Backward compatibility - weights
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
    'EnergyConfig',
    'CostWeights',
    'NormalizationConfig',
    'APIConfig',
    'ExploringAntConfig',
    'DEFAULT_CONFIG',
    # Backward compatibility
    'K_ENERGY',
    'K_TIME',
    'EPSILON',
    'FALLBACK_NORM_ENERGY_KJ',
    'FALLBACK_NORM_TFT_SEC',
    'RESERVATION_API_URL',
    # Physics parameters
    'MASS_AGV',
    'FRICTION_COEFF',
    'GRAVITY',
    'MOTOR_EFFICIENCY',
    'MAX_VELOCITY',
    'ACCELERATION',
    'IDLE_POWER',
]
