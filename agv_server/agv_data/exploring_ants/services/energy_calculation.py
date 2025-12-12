"""
Physics-Based Energy Calculation Service for Exploring Ant

This module provides physics-based energy calculation logic for AGV operations
using kinetic energy, friction forces, and motor efficiency.

Based on: 'Energy and Time-Efficient Scheduling of Automated Guided Vehicles System'
(Section II.B, Equations 2-10)
"""

import math
from ..config import EnergyConfig, DEFAULT_CONFIG


class EnergyCalculationService:
    """
    Physics-based service for calculating energy consumption of AGV operations.
    
    This service uses fundamental physics to model energy consumption:
    - Kinetic energy for acceleration/deceleration
    - Rolling friction forces
    - Motor efficiency losses
    - Idle power consumption
    
    The calculation uses a Trapezoidal Velocity Profile:
    1. Acceleration phase: overcome friction + build kinetic energy
    2. Cruising phase: maintain velocity against friction
    3. Deceleration phase: dissipate kinetic energy (no regen assumed)
    
    Attributes:
        config: Physics-based energy configuration
    
    Example:
        >>> service = EnergyCalculationService()
        >>> # 100kg load over 50m
        >>> energy = service.calculate_travel_energy(distance_m=50.0, load_kg=100.0)
        >>> print(f"Energy: {energy} kJ")
    """
    
    def __init__(self, config: EnergyConfig = None):
        """
        Initialize the physics-based energy calculation service.
        
        Args:
            config: Energy configuration. If None, uses DEFAULT_CONFIG.energy
        """
        self.config = config or DEFAULT_CONFIG.energy
        self._validate_config()
    
    def _validate_config(self):
        """Validate physics parameters are physically reasonable."""
        if self.config.mass_agv <= 0:
            raise ValueError(f"mass_agv must be positive, got {self.config.mass_agv}")
        if self.config.max_velocity <= 0:
            raise ValueError(f"max_velocity must be positive, got {self.config.max_velocity}")
        if self.config.acceleration <= 0:
            raise ValueError(f"acceleration must be positive, got {self.config.acceleration}")
        if not 0 < self.config.motor_efficiency <= 1.0:
            raise ValueError(f"motor_efficiency must be in (0, 1], got {self.config.motor_efficiency}")
        if self.config.friction_coeff < 0:
            raise ValueError(f"friction_coeff cannot be negative, got {self.config.friction_coeff}")
    
    def calculate_travel_energy(self, distance_m: float, load_kg: float) -> float:
        """
        Calculate physics-based energy consumption for traveling with a load.
        
        Uses Trapezoidal or Triangular velocity profile depending on distance.
        Considers:
        - Rolling friction: F_fr = (m_agv + m_load) * g * μ_r
        - Inertia during acceleration: F_in = (m_agv + m_load) * a
        - Motor efficiency losses: E_electric = W_mechanical / η
        - Idle power during motion: E_idle = P_idle * t_total
        
        Args:
            distance_m: Distance to travel in meters
            load_kg: Load weight in kilograms
            
        Returns:
            float: Energy consumption in kilojoules (kJ)
            
        Raises:
            ValueError: If distance_m or load_kg is negative
            
        Example:
            >>> service = EnergyCalculationService()
            >>> # Physics-based calculation for 100kg load over 50m
            >>> energy = service.calculate_travel_energy(50.0, 100.0)
            >>> # Considers friction, inertia, motor efficiency
            >>> print(f"Energy: {energy:.3f} kJ")
        """
        if distance_m < 0:
            raise ValueError(f"distance_m cannot be negative, got {distance_m}")
        if load_kg < 0:
            raise ValueError(f"load_kg cannot be negative, got {load_kg}")
        
        # Zero distance → zero energy
        if distance_m == 0:
            return 0.0
        
        # Total mass (AGV + load)
        total_mass = self.config.mass_agv + load_kg
        
        # Rolling friction force (constant)
        f_friction = total_mass * self.config.gravity * self.config.friction_coeff
        
        # Determine velocity profile type
        # Distance to reach v_max and stop: d_min = v_max²/a
        v_max = self.config.max_velocity
        a = self.config.acceleration
        d_min = (v_max ** 2) / a
        
        if distance_m >= d_min:
            # Trapezoidal profile: can reach v_max
            energy_j = self._calculate_trapezoidal_energy(
                distance_m, total_mass, f_friction, v_max, a
            )
            total_time = self._calculate_trapezoidal_time(distance_m, v_max, a)
        else:
            # Triangular profile: cannot reach v_max
            energy_j = self._calculate_triangular_energy(
                distance_m, total_mass, f_friction, a
            )
            total_time = self._calculate_triangular_time(distance_m, a)
        
        # Add idle power consumption
        energy_idle_j = self.config.idle_power * total_time
        total_energy_j = energy_j + energy_idle_j
        
        # Convert to kJ
        return total_energy_j / 1000.0
    
    def _calculate_trapezoidal_energy(
        self, distance: float, mass: float, f_friction: float, v_max: float, a: float
    ) -> float:
        """
        Calculate mechanical energy for trapezoidal velocity profile.
        
        Phases:
        1. Acceleration (0 → v_max): kinetic energy + friction work
        2. Cruising (v_max constant): friction work only
        3. Deceleration (v_max → 0): kinetic dissipated (no regen)
        
        Args:
            distance: Total distance (m)
            mass: Total mass (kg)
            f_friction: Rolling friction force (N)
            v_max: Maximum velocity (m/s)
            a: Acceleration (m/s²)
        
        Returns:
            float: Mechanical energy in Joules, converted to electrical via efficiency
        """
        # Distances for acceleration and deceleration
        d_accel = (v_max ** 2) / (2 * a)
        d_decel = d_accel  # Symmetric
        d_cruise = distance - d_accel - d_decel
        
        # Phase 1: Acceleration
        # Kinetic energy gained: ΔKE = 0.5 * m * v_max²
        kinetic_energy = 0.5 * mass * (v_max ** 2)
        # Work against friction during acceleration: W_fr_accel = F_fr * d_accel
        work_friction_accel = f_friction * d_accel
        work_accel = kinetic_energy + work_friction_accel
        
        # Phase 2: Cruising
        # Work against friction: W_fr_cruise = F_fr * d_cruise
        work_cruise = f_friction * d_cruise
        
        # Phase 3: Deceleration
        # Kinetic energy dissipated (no regenerative braking assumed)
        # Friction helps braking, so motor provides less force
        # Conservative approach: assume no electrical energy needed for deceleration
        # (friction + braking dissipate kinetic energy mechanically)
        work_decel = 0.0
        
        # Total mechanical work
        work_mechanical = work_accel + work_cruise + work_decel
        
        # Convert to electrical energy (account for motor efficiency)
        energy_electric = work_mechanical / self.config.motor_efficiency
        
        return energy_electric
    
    def _calculate_triangular_energy(
        self, distance: float, mass: float, f_friction: float, a: float
    ) -> float:
        """
        Calculate mechanical energy for triangular velocity profile.
        
        Cannot reach v_max, so:
        - Acceleration to v_peak
        - Immediate deceleration to 0
        - No cruising phase
        
        Args:
            distance: Total distance (m)
            mass: Total mass (kg)
            f_friction: Rolling friction force (N)
            a: Acceleration (m/s²)
        
        Returns:
            float: Electrical energy in Joules
        """
        # Peak velocity: v_peak = sqrt(a * distance)
        v_peak = math.sqrt(a * distance)
        
        # Distance split evenly between accel and decel
        d_accel = distance / 2.0
        
        # Kinetic energy at peak
        kinetic_energy = 0.5 * mass * (v_peak ** 2)
        
        # Work against friction during acceleration
        work_friction_accel = f_friction * d_accel
        
        # Total work (accel only; decel is passive)
        work_mechanical = kinetic_energy + work_friction_accel
        
        # Convert to electrical
        energy_electric = work_mechanical / self.config.motor_efficiency
        
        return energy_electric
    
    def _calculate_trapezoidal_time(self, distance: float, v_max: float, a: float) -> float:
        """Calculate total time for trapezoidal profile."""
        d_accel = (v_max ** 2) / (2 * a)
        d_decel = d_accel
        d_cruise = distance - d_accel - d_decel
        
        t_accel = v_max / a
        t_decel = t_accel
        t_cruise = d_cruise / v_max
        
        return t_accel + t_cruise + t_decel
    
    def _calculate_triangular_time(self, distance: float, a: float) -> float:
        """Calculate total time for triangular profile."""
        v_peak = math.sqrt(a * distance)
        t_accel = v_peak / a
        t_decel = t_accel
        return t_accel + t_decel
    
    def calculate_wait_energy(self, delay_sec: float) -> float:
        """
        Calculate energy consumption while waiting (idle).
        
        Formula: E_wait = idle_power * delay_sec / 1000
        
        Args:
            delay_sec: Delay time in seconds
            
        Returns:
            float: Energy consumption in kilojoules (kJ)
            
        Raises:
            ValueError: If delay_sec is negative
            
        Note:
            idle_power is in Watts (W = J/s)
            - 0.1 W * 60 s = 6 J = 0.006 kJ
            - Division by 1000 converts J to kJ
            
        Example:
            >>> service = EnergyCalculationService()
            >>> # 60 second delay
            >>> energy = service.calculate_wait_energy(60.0)
            >>> # E = 0.1 * 60 / 1000 = 0.006 kJ
            >>> print(f"Wait energy: {energy} kJ")
            Wait energy: 0.006 kJ
        """
        if delay_sec < 0:
            raise ValueError(f"delay_sec cannot be negative, got {delay_sec}")
        
        return self.config.idle_power * delay_sec / 1000.0
    
    def calculate_total_energy(
        self, 
        travel_distance_m: float, 
        load_kg: float,
        wait_time_sec: float
    ) -> float:
        """
        Calculate total energy for a journey segment (travel + wait).
        
        Args:
            travel_distance_m: Distance traveled in meters
            load_kg: Load weight in kilograms
            wait_time_sec: Time spent waiting in seconds
            
        Returns:
            float: Total energy consumption in kilojoules (kJ)
            
        Example:
            >>> service = EnergyCalculationService()
            >>> total = service.calculate_total_energy(
            ...     travel_distance_m=50.0,
            ...     load_kg=100.0,
            ...     wait_time_sec=30.0
            ... )
            >>> # E_travel = 12.5 kJ, E_wait = 0.003 kJ
            >>> print(f"Total energy: {total} kJ")
        """
        travel_energy = self.calculate_travel_energy(travel_distance_m, load_kg)
        wait_energy = self.calculate_wait_energy(wait_time_sec)
        return travel_energy + wait_energy
