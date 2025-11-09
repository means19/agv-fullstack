"""
Constants for AGV Agent Logic (Exploring Ant - DMAS-ET)

This file contains all constants used in the DMAS-ET algorithm
as specified in agv_agent_logic.md
"""

# ============================================================
# Cost Function Weights
# ============================================================
K_ENERGY = 0.5      # Weight for energy component in cost function
K_TIME = 0.5        # Weight for time component (TFT - Total Flow Time) in cost function

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
# Dynamic Normalization Parameters
# ============================================================
# Epsilon (ε) weight to balance MiniSum and MiniMax objectives
# epsilon = 1.0 -> Pure efficiency (MiniSum only)
# epsilon = 0.0 -> Pure load balancing (MiniMax only)
# epsilon = 0.5 -> 50/50 balance
EPSILON = 0.5

# Fallback normalization values (used when baseline = 0)
FALLBACK_NORM_ENERGY_KJ = 1.0   # kJ
FALLBACK_NORM_TFT_SEC = 1.0     # seconds

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

Total Cost (Legacy - for reference):
    J = K_ENERGY * total_energy_kJ + K_TIME * total_tft_sec
    
    Example with 50 kJ energy and 120 sec total flow time:
    J = 0.5 * 50 + 0.5 * 120
      = 25 + 60
      = 85
    
    Note: Changed from K_TARDINESS (SOT - Sum of Tardiness) to K_TIME (TFT - Total Flow Time).
    TFT is always positive and measures overall performance, not just lateness.
    
    With Dynamic Normalization, the actual bidding calculation is:
    - Calculate baseline costs (E_baseline, TFT_baseline) using ideal Dijkstra
    - Calculate marginal costs (E_marginal, TFT_marginal) using DMAS-ET
    - Normalize: E_norm = E_marginal / E_baseline
    - Combine MiniSum and MiniMax using EPSILON weight
"""
