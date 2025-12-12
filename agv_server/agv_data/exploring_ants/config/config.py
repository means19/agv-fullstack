"""
Configuration for Exploring Ant (DMAS-ET)

This module defines configuration classes for the Exploring Ant algorithm.
All constants are organized into typed dataclasses for better maintainability.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class EnergyConfig:
    """
    Physics-based configuration for energy calculations.
    
    This configuration uses fundamental physics parameters instead of
    simple coefficients to model AGV energy consumption.
    
    Attributes:
        mass_agv: Mass of AGV without load (kg)
        friction_coeff: Rolling resistance coefficient (μ_r), typical 0.02-0.03
        gravity: Gravitational acceleration (m/s²), standard 9.81
        motor_efficiency: Motor efficiency (η), typical 0.6-0.8
        max_velocity: Maximum cruise velocity (m/s)
        acceleration: Acceleration/deceleration rate (m/s²)
        idle_power: Idle power consumption in W (watts) when AGV is waiting
    
    Physics Formulas:
        F_friction = (m_agv + m_load) * g * μ_r
        F_inertia = (m_agv + m_load) * a
        P_motion = (F_friction + F_inertia) * v
        P_electric = P_motion / η + P_idle
    
    Example:
        >>> config = EnergyConfig()
        >>> print(f"AGV mass: {config.mass_agv} kg")
        >>> print(f"Max velocity: {config.max_velocity} m/s")
    """
    mass_agv: float = 40.0              # kg - typical small AGV
    friction_coeff: float = 0.025       # μ_r - rolling resistance
    gravity: float = 9.81               # m/s² - standard gravity
    motor_efficiency: float = 0.7       # η - 70% efficiency
    max_velocity: float = 1.0           # m/s - 1 meter per second
    acceleration: float = 1.0           # m/s² - moderate acceleration
    idle_power: float = 0.1             # W - auxiliary systems


@dataclass
class CostWeights:
    """
    Weights for cost function components.
    
    Attributes:
        k_energy: Weight for energy component in cost function
        k_time: Weight for time component (TFT) in cost function
    
    Note:
        k_energy + k_time should equal 1.0 for balanced weighting
    """
    k_energy: float = 0.5
    k_time: float = 1.0 - k_energy
    
    def __post_init__(self):
        """Validate that weights sum to 1.0"""
        total = self.k_energy + self.k_time
        if not 0.99 <= total <= 1.01:  # Allow small floating point tolerance
            raise ValueError(
                f"Cost weights should sum to 1.0, got {total} "
                f"(k_energy={self.k_energy}, k_time={self.k_time})"
            )


@dataclass
class NormalizationConfig:
    """
    Configuration for dynamic normalization.
    
    Attributes:
        epsilon: Balance weight between MiniSum and MiniMax objectives
                 - 1.0: Pure efficiency (MiniSum only)
                 - 0.0: Pure load balancing (MiniMax only)
                 - 0.5: 50/50 balance
        fallback_norm_energy_kj: Fallback normalization value for energy when baseline = 0
        fallback_norm_tft_sec: Fallback normalization value for TFT when baseline = 0
    """
    epsilon: float = 0.5
    fallback_norm_energy_kj: float = 1.0
    fallback_norm_tft_sec: float = 1.0
    
    def __post_init__(self):
        """Validate epsilon is in valid range"""
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError(f"epsilon must be between 0 and 1, got {self.epsilon}")


@dataclass
class APIConfig:
    """
    Configuration for external API connections.
    
    Attributes:
        reservation_api_url: Base URL for Reservation Table API
        request_timeout_sec: Timeout for API requests in seconds
    """
    reservation_api_url: str = "http://localhost:8000/api/agvs/reservation"
    request_timeout_sec: int = 5


@dataclass
class ExploringAntConfig:
    """
    Main configuration container for Exploring Ant algorithm.
    
    This class aggregates all configuration sections and provides
    a single point of access for all algorithm parameters.
    
    Attributes:
        energy: Energy calculation configuration
        cost_weights: Cost function weights
        normalization: Dynamic normalization configuration
        api: API connection configuration
    
    Example:
        >>> config = ExploringAntConfig()
        >>> print(f"Base energy: {config.energy.c_base} kJ/m")
        >>> print(f"Epsilon: {config.normalization.epsilon}")
        >>> 
        >>> # Custom configuration
        >>> custom_config = ExploringAntConfig(
        ...     energy=EnergyConfig(c_base=0.1, c_load_coeff=0.003),
        ...     normalization=NormalizationConfig(epsilon=0.7)
        ... )
    """
    energy: EnergyConfig = None
    cost_weights: CostWeights = None
    normalization: NormalizationConfig = None
    api: APIConfig = None
    
    def __post_init__(self):
        """Initialize nested configs with defaults if not provided."""
        if self.energy is None:
            self.energy = EnergyConfig()
        if self.cost_weights is None:
            self.cost_weights = CostWeights()
        if self.normalization is None:
            self.normalization = NormalizationConfig()
        if self.api is None:
            self.api = APIConfig()
    
    @classmethod
    def default(cls) -> 'ExploringAntConfig':
        """
        Create a configuration with default values.
        
        Returns:
            ExploringAntConfig: Configuration with all defaults
        """
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'ExploringAntConfig':
        """
        Create configuration from a dictionary.
        
        Args:
            config_dict: Dictionary with configuration values
        
        Returns:
            ExploringAntConfig: Configuration instance
        
        Example:
            >>> config_dict = {
            ...     'energy': {'c_base': 0.1},
            ...     'normalization': {'epsilon': 0.7}
            ... }
            >>> config = ExploringAntConfig.from_dict(config_dict)
        """
        energy = EnergyConfig(**config_dict.get('energy', {}))
        cost_weights = CostWeights(**config_dict.get('cost_weights', {}))
        normalization = NormalizationConfig(**config_dict.get('normalization', {}))
        api = APIConfig(**config_dict.get('api', {}))
        
        return cls(
            energy=energy,
            cost_weights=cost_weights,
            normalization=normalization,
            api=api
        )


# Default global configuration instance
DEFAULT_CONFIG: ExploringAntConfig = ExploringAntConfig.default()


# Backward compatibility exports (for existing code using direct imports)
K_ENERGY = DEFAULT_CONFIG.cost_weights.k_energy
K_TIME = DEFAULT_CONFIG.cost_weights.k_time
EPSILON = DEFAULT_CONFIG.normalization.epsilon
FALLBACK_NORM_ENERGY_KJ = DEFAULT_CONFIG.normalization.fallback_norm_energy_kj
FALLBACK_NORM_TFT_SEC = DEFAULT_CONFIG.normalization.fallback_norm_tft_sec
RESERVATION_API_URL = DEFAULT_CONFIG.api.reservation_api_url

# Physics-based parameters (new)
MASS_AGV = DEFAULT_CONFIG.energy.mass_agv
FRICTION_COEFF = DEFAULT_CONFIG.energy.friction_coeff
GRAVITY = DEFAULT_CONFIG.energy.gravity
MOTOR_EFFICIENCY = DEFAULT_CONFIG.energy.motor_efficiency
MAX_VELOCITY = DEFAULT_CONFIG.energy.max_velocity
ACCELERATION = DEFAULT_CONFIG.energy.acceleration
IDLE_POWER = DEFAULT_CONFIG.energy.idle_power
