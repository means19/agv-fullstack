"""
Constants for AGV Agent Logic (Exploring Ant - DMAS-ET)

This file contains all constants used in the DMAS-ET algorithm
as specified in agv_agent_logic.md
"""

# ============================================================
# Cost Function Weights
# ============================================================
K_ENERGY = 0.5      # Weight for energy component in cost function
K_TARDINESS = 0.5   # Weight for tardiness component in cost function

# ============================================================
# Energy Calculation Constants
# ============================================================
C_BASE = 0.05           # Base energy consumption in kJ/m (kilojoules per meter)
C_LOAD_COEFF = 0.002    # Load coefficient in kJ/(kg·m) - additional energy per kg of load per meter
P_IDLE = 0.1            # Idle power consumption in W (watts) when AGV is waiting

# ============================================================
# API Configuration
# ============================================================
# Base URL for Reservation Table API
# In production, this should be configured via environment variable
RESERVATION_API_URL = "http://localhost:8000/api/agvs/reservation"

# ============================================================
# Notes on Energy Calculations
# ============================================================
"""
Travel Energy:
    E_travel = (C_BASE + C_LOAD_COEFF * load_kg) * distance_m
    
    Example with 100kg load over 50m:
    E_travel = (0.05 + 0.002 * 100) * 50
             = (0.05 + 0.2) * 50
             = 0.25 * 50
             = 12.5 kJ

Wait Energy:
    E_wait = P_IDLE * delay_sec / 1000
    
    Example with 60 second delay:
    E_wait = 0.1 * 60 / 1000
           = 6 / 1000
           = 0.006 kJ
    
    Note: P_IDLE is in Watts (W = J/s), so:
    - 0.1 W * 60 s = 6 J
    - 6 J / 1000 = 0.006 kJ
    (Division by 1000 converts J to kJ)

Total Cost:
    J = K_ENERGY * total_energy_kJ + K_TARDINESS * total_tardiness_sec
    
    Example with 50 kJ energy and 120 sec tardiness:
    J = 0.5 * 50 + 0.5 * 120
      = 25 + 60
      = 85
"""
