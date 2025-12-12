# Exploring Ants Architecture

## Package Structure

```
agv_data/exploring_ants/
│
├── models/                     # Data Models
│   ├── __init__.py
│   └── route_step.py          # RouteStep dataclass
│
├── services/                   # Business Logic
│   ├── __init__.py
│   ├── energy_calculation.py  # Energy calculations
│   └── exploring_ant_service.py # Main DMAS-ET algorithm
│
├── clients/                    # External API Clients
│   ├── __init__.py
│   └── reservation_table_client.py # Reservation Table API
│
├── config/                     # Configuration Management
│   ├── __init__.py
│   └── config.py              # Typed configuration classes
│
└── __init__.py                # Main package exports
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Exploring Ants Package                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         ExploringAntService (Orchestrator)          │    │
│  │                                                     │    │
│  │  + explore(route, start_time) → (energy, tft)       │    │
│  │  + explore_silent(...) → (energy, tft)              │    │
│  └──────────────┬──────────────────┬───────────────────┘    │
│                 │                  │                        │
│        ┌────────┴────────┐  ┌──────┴─────────┐              │
│        │                 │  │                │              │
│  ┌─────▼──────────┐  ┌───▼──▼──────────┐  ┌──▼─────────┐    │
│  │ EnergyCalc     │  │ ReservationTable│  │ Output     │    │
│  │ Service        │  │ Client          │  │ Strategy   │    │
│  │                │  │                 │  │            │    │
│  │ + calc_travel  │  │ + query_slot    │  │ Verbose    │    │
│  │ + calc_wait    │  │ + query_safe    │  │ Silent     │    │
│  │ + calc_total   │  │ + validate      │  └────────────┘    │
│  └────────────────┘  └─────────────────┘                    │
│                                                             │
│  ┌──────────────┐   ┌─────────────────────────────────┐     │
│  │ RouteStep    │   │  ExploringAntConfig             │     │
│  │ (dataclass)  │   │                                 │     │
│  │              │   │  ├─ EnergyConfig                │     │
│  │ + resource_id│   │  ├─ CostWeights                 │     │
│  │ + distance_m │   │  ├─ NormalizationConfig         │     │
│  │ + duration_s │   │  └─ APIConfig                   │     │
│  │ + load_kg    │   └─────────────────────────────────┘     │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Client Request
   │
   ├─→ ExploringAntService.explore(route_plan, start_time)
   │
2. Initialization
   │
   ├─→ Load Configuration (ExploringAntConfig)
   ├─→ Initialize EnergyCalculationService
   ├─→ Initialize ReservationTableClient
   └─→ Set OutputStrategy (Verbose/Silent)
   │
3. Route Exploration Loop
   │
   ├─→ For each RouteStep:
   │   │
   │   ├─→ ReservationTableClient.query_slot()
   │   │   │
   │   │   ├─→ HTTP POST to Reservation API
   │   │   └─→ Parse earliest_available_start
   │   │
   │   ├─→ Calculate delay (if any)
   │   │   │
   │   │   └─→ EnergyCalculationService.calculate_wait_energy()
   │   │
   │   ├─→ EnergyCalculationService.calculate_travel_energy()
   │   │
   │   ├─→ Update current_time
   │   │
   │   ├─→ Track TFT (if task endpoint)
   │   │
   │   └─→ OutputStrategy.log_step()
   │
4. Return Results
   │
   └─→ (total_energy_kj, total_tft_sec)
```

## Design Patterns

### 1. Service Layer Pattern
```python
# Business logic separated into focused services
ExploringAntService     # Algorithm orchestration
EnergyCalculationService # Energy calculations
ReservationTableClient   # External API communication
```

### 2. Dependency Injection
```python
service = ExploringAntService(
    energy_service=my_energy_service,    # Injected
    reservation_client=my_client,         # Injected
    config=my_config,                     # Injected
    verbose=True
)
```

### 3. Strategy Pattern
```python
# Flexible output behavior
OutputStrategy (ABC)
    ├─ VerboseOutput   # Detailed console logging
    └─ SilentOutput    # No output (performance)

# Easy to extend:
    ├─ MetricsOutput   # Performance metrics
    └─ LoggingOutput   # File logging
```

### 4. Configuration Pattern
```python
# Typed configuration management
@dataclass
class ExploringAntConfig:
    energy: EnergyConfig
    cost_weights: CostWeights
    normalization: NormalizationConfig
    api: APIConfig
    
    @classmethod
    def from_dict(config_dict: dict) -> 'ExploringAntConfig'
```

## Integration Points

### 1. Auctioneer Service
```python
# Uses baseline calculation
from agv_services.auctioneer_service import calculate_baseline_simple
from agv_data.exploring_ants import ExploringAntService

# Calculate baseline
E_baseline, TFT_baseline = calculate_baseline_simple(...)

# Calculate marginal cost
service = ExploringAntService(verbose=False)
E_marginal, TFT_marginal = service.explore_silent(route, start_time)
```

### 2. Bidding Service
```python
# Uses DMAS-ET for bid calculation
from agv_services.bidding_service import BiddingService
from agv_data.exploring_ants import RouteStep

# Create route plan
route = [RouteStep(...), RouteStep(...)]

# Calculate bid (uses DMAS_ET_silent internally)
bid = bidding_service.calculate_bid_for_agv(agv, order, E_base, TFT_base)
```

### 3. Reservation Table API
```python
# External HTTP API
POST /api/agvs/reservation/resource/{id}/query_slot/
{
    "request_start_time": "2025-01-15T10:00:00+00:00",
    "duration_seconds": 30
}

Response:
{
    "earliest_available_start": "2025-01-15T10:02:00+00:00"
}
```

## Class Hierarchy

```
RouteStep (dataclass)
  ├─ resource_id: int
  ├─ distance_m: float
  ├─ duration_sec: float
  ├─ load_kg: float
  ├─ is_task_endpoint: bool
  └─ due_date: Optional[datetime]

ExploringAntConfig (dataclass)
  ├─ energy: EnergyConfig (Physics-Based)
  │   ├─ mass_agv: float = 40.0 kg
  │   ├─ friction_coeff: float = 0.025 (μ_r)
  │   ├─ gravity: float = 9.81 m/s²
  │   ├─ motor_efficiency: float = 0.7 (η)
  │   ├─ max_velocity: float = 1.0 m/s
  │   ├─ acceleration: float = 1.0 m/s²
  │   └─ idle_power: float = 0.1 W
  ├─ cost_weights: CostWeights
  │   ├─ k_energy: float = 0.5
  │   └─ k_time: float = 0.5
  ├─ normalization: NormalizationConfig
  │   ├─ epsilon: float = 0.5
  │   ├─ fallback_norm_energy_kj: float = 1.0
  │   └─ fallback_norm_tft_sec: float = 1.0
  └─ api: APIConfig
      ├─ reservation_api_url: str
      └─ request_timeout_sec: int = 5

OutputStrategy (ABC)
  ├─ log_start(...)
  ├─ log_step(...)
  ├─ log_task_endpoint(...)
  ├─ log_completion(...)
  └─ log_error(...)
      ├─ VerboseOutput
      └─ SilentOutput

EnergyCalculationService
  ├─ config: EnergyConfig
  ├─ calculate_travel_energy(distance_m, load_kg) → float
  ├─ calculate_wait_energy(delay_sec) → float
  └─ calculate_total_energy(travel_dist, load, wait_time) → float

ReservationTableClient
  ├─ config: APIConfig
  ├─ query_slot(resource_id, desired_start, duration) → Dict
  ├─ query_slot_safe(...) → Optional[Dict]
  ├─ validate_response(response) → bool
  └─ parse_earliest_start(response) → Optional[datetime]

ExploringAntService
  ├─ energy_service: EnergyCalculationService
  ├─ reservation_client: ReservationTableClient
  ├─ config: ExploringAntConfig
  ├─ output_strategy: OutputStrategy
  ├─ explore(route, start_time, agv_id) → Tuple[float, float]
  └─ explore_silent(route, start_time, agv_id) → Tuple[float, float]
```

## Usage Examples

### Basic Usage (Verbose)
```python
from agv_data.exploring_ants import ExploringAntService, RouteStep
from datetime import datetime, timezone

# Create service (verbose by default)
service = ExploringAntService()

# Create route plan
route = [
    RouteStep(
        resource_id=1,
        distance_m=50.0,
        duration_sec=30.0,
        load_kg=0.0,
        is_task_endpoint=False
    ),
    RouteStep(
        resource_id=2,
        distance_m=100.0,
        duration_sec=60.0,
        load_kg=100.0,
        is_task_endpoint=True
    )
]

# Explore route
energy, tft = service.explore(
    route_plan=route,
    global_start_time=datetime.now(timezone.utc),
    agv_id="AGV-01"
)

print(f"Energy: {energy} kJ, TFT: {tft}s")
```

### Silent Mode (Performance)
```python
from agv_data.exploring_ants import ExploringAntService

# Create silent service
service = ExploringAntService(verbose=False)

# Explore route (no console output)
energy, tft = service.explore(route, start_time, "AGV-01")
```

### Custom Configuration
```python
from agv_data.exploring_ants import (
    ExploringAntService,
    ExploringAntConfig,
    EnergyConfig,
    NormalizationConfig
)

# Create custom config
config = ExploringAntConfig(
    energy=EnergyConfig(
        c_base=0.1,           # Higher base energy
        c_load_coeff=0.003    # Higher load coefficient
    ),
    normalization=NormalizationConfig(
        epsilon=0.7           # More weight on efficiency (MiniSum)
    )
)

# Use custom config
service = ExploringAntService(config=config)
energy, tft = service.explore(route, start_time)
```

### Dependency Injection (Testing)
```python
from agv_data.exploring_ants import (
    ExploringAntService,
    EnergyCalculationService,
    ReservationTableClient
)

# Mock services for testing
class MockReservationClient(ReservationTableClient):
    def query_slot(self, resource_id, desired_start, duration_sec):
        # Return mock response
        return {
            'earliest_available_start': desired_start.isoformat()
        }

# Inject mock
mock_client = MockReservationClient()
service = ExploringAntService(
    reservation_client=mock_client,
    verbose=False
)

# Test with mock (no real API calls)
energy, tft = service.explore(route, start_time)
```

## Key Principles

### Single Responsibility
- Each class has ONE reason to change
- `EnergyCalculationService`: Only energy calculations
- `ReservationTableClient`: Only API communication
- `ExploringAntService`: Only algorithm orchestration

### Open/Closed Principle
- Open for extension (new OutputStrategy implementations)
- Closed for modification (base classes stable)

### Dependency Inversion
- High-level modules depend on abstractions (OutputStrategy)
- Low-level implementations injected at runtime

### Interface Segregation
- Small, focused interfaces
- Clients not forced to depend on unused methods

### Don't Repeat Yourself (DRY)
- Configuration centralized in config classes
- Energy calculations reused across services
- API client shared by all consumers

## Physics-Based Energy Model

### Overview
The energy calculation system uses a **physics-based kinetic model** instead of simple linear coefficients. This approach models the actual physical forces and energy transformations during AGV motion.

**Reference**: Based on "Energy and Time-Efficient Scheduling of Automated Guided Vehicles System" (Section II.B, Equations 2-10)

### Core Physics Principles

#### 1. Power Consumption
```
P_electric = (P_motion / η) + P_idle

Where:
  P_motion = (F_friction + F_inertia) × v
  η = motor efficiency (0.7 = 70%)
  P_idle = auxiliary power (sensors, CPU)
```

#### 2. Forces
**Rolling Friction** (constant during motion):
```
F_friction = (m_agv + m_load) × g × μ_r

Where:
  m_agv = AGV mass (40 kg)
  m_load = payload mass (variable)
  g = gravity (9.81 m/s²)
  μ_r = rolling resistance coefficient (0.025)
```

**Inertia** (during acceleration/deceleration):
```
F_inertia = (m_agv + m_load) × a

Where:
  a = acceleration rate (1.0 m/s²)
```

### Velocity Profile

#### Trapezoidal Profile (Long Distance)
For distances where AGV can reach max velocity:

```
  v_max |     ████████████
        |    ╱            ╲
        |   ╱              ╲
      0 |__╱________________╲__
        
        Accel   Cruise   Decel
        
Phases:
1. Acceleration (0 → v_max):
   - Build kinetic energy: ΔKE = 0.5 × m × v_max²
   - Overcome friction: W_fr = F_friction × d_accel
   - Work = ΔKE + W_fr

2. Cruising (v_max constant):
   - Maintain velocity against friction
   - Work = F_friction × d_cruise

3. Deceleration (v_max → 0):
   - Kinetic energy dissipated
   - No electrical energy needed (friction helps braking)
```

**Distances**:
```
d_accel = v_max² / (2a)
d_decel = d_accel  (symmetric)
d_cruise = distance_total - d_accel - d_decel
```

**Energy Calculation**:
```python
# Phase 1: Acceleration
kinetic_energy = 0.5 * mass * v_max²
work_friction_accel = f_friction * d_accel
work_accel = kinetic_energy + work_friction_accel

# Phase 2: Cruising
work_cruise = f_friction * d_cruise

# Phase 3: Deceleration
work_decel = 0.0  # No regen, friction helps

# Total
work_mechanical = work_accel + work_cruise + work_decel
energy_electric = work_mechanical / motor_efficiency
energy_idle = idle_power * total_time
total_energy = (energy_electric + energy_idle) / 1000  # kJ
```

#### Triangular Profile (Short Distance)
For distances too short to reach v_max:

```
  v_peak |      ╱╲
         |     ╱  ╲
         |    ╱    ╲
       0 |___╱______╲___
         
         Accel  Decel

Peak velocity:
  v_peak = √(a × distance)

Energy:
  kinetic_energy = 0.5 × m × v_peak²
  work_friction = f_friction × (distance/2)
  work_total = kinetic_energy + work_friction
  energy_electric = work_total / motor_efficiency
```

**Threshold**:
```
d_min = v_max² / a

If distance >= d_min: Use Trapezoidal
If distance < d_min:  Use Triangular
```

### Configuration Parameters

```python
@dataclass
class EnergyConfig:
    mass_agv: float = 40.0           # kg - AGV base mass
    friction_coeff: float = 0.025    # μ_r - rolling resistance
    gravity: float = 9.81            # m/s² - gravitational constant
    motor_efficiency: float = 0.7    # η - 70% efficiency
    max_velocity: float = 1.0        # m/s - cruise speed
    acceleration: float = 1.0        # m/s² - accel/decel rate
    idle_power: float = 0.1          # W - auxiliary systems
```

### Comparison: Old vs New Model

#### Old Model (Linear Coefficients)
```python
E = (c_base + c_load_coeff × load) × distance
E = (0.05 + 0.002 × 100) × 50
E = 0.25 × 50 = 12.5 kJ
```

**Limitations**:
- Assumes linear relationship (not physically accurate)
- No velocity profile consideration
- Ignores acceleration phase energy
- Cannot distinguish short vs long distances
- No motor efficiency modeling

#### New Model (Physics-Based)
```python
# 100kg load, 50m distance
total_mass = 40 + 100 = 140 kg
f_friction = 140 × 9.81 × 0.025 = 34.335 N
d_min = 1.0² / 1.0 = 1.0 m

# Distance 50m >= 1m → Trapezoidal
d_accel = 0.5 m
d_cruise = 49 m
d_decel = 0.5 m

kinetic = 0.5 × 140 × 1² = 70 J
work_accel = 70 + 34.335×0.5 = 87.17 J
work_cruise = 34.335 × 49 = 1682.42 J
work_total = 87.17 + 1682.42 = 1769.59 J

energy_electric = 1769.59 / 0.7 = 2528 J
time = 0.5 + 49 + 0.5 = 50 s
energy_idle = 0.1 × 50 = 5 J

total = (2528 + 5) / 1000 = 2.533 kJ
```

**Advantages**:
- ✅ Physically accurate force modeling
- ✅ Non-linear relationship with mass
- ✅ Velocity profile awareness
- ✅ Distinguishes acceleration vs cruising
- ✅ Motor efficiency losses modeled
- ✅ Idle power during motion
- ✅ Suitable for research papers

### Scientific Justification

1. **Non-linearity**: Energy depends on v² (kinetic) and varies with distance non-linearly
2. **Load dependency**: Friction and inertia scale with total mass (m_agv + m_load)
3. **Phase separation**: Different energy mechanisms in accel/cruise/decel phases
4. **Efficiency modeling**: Separates mechanical work from electrical consumption
5. **Realistic parameters**: Uses measurable physical constants (μ_r, η, g)

### Usage Examples

#### Basic Usage
```python
from agv_data.exploring_ants import EnergyCalculationService

service = EnergyCalculationService()

# Physics-based calculation
energy = service.calculate_travel_energy(
    distance_m=50.0,
    load_kg=100.0
)
# Returns: 2.533 kJ (not 12.5 kJ from old model)
```

#### Custom Physics Parameters
```python
from agv_data.exploring_ants import EnergyConfig, EnergyCalculationService

# Heavier AGV with better motor
config = EnergyConfig(
    mass_agv=60.0,           # Heavier AGV
    motor_efficiency=0.85,   # Better motor
    friction_coeff=0.02      # Smoother wheels
)

service = EnergyCalculationService(config=config)
energy = service.calculate_travel_energy(50.0, 100.0)
```

#### Short Distance (Triangular Profile)
```python
# 0.5m distance - too short to reach v_max
energy_short = service.calculate_travel_energy(
    distance_m=0.5,
    load_kg=100.0
)
# Uses triangular profile automatically
```

### Validation & Testing

**Test Cases**:
1. **Zero distance**: Should return 0 kJ
2. **Triangular threshold**: Compare d < d_min vs d > d_min
3. **Load variation**: Heavy load should increase energy non-linearly
4. **Parameter validation**: Negative values should raise errors

**Expected Behavior**:
- Energy increases with load (but not linearly)
- Short distances use less energy per meter (less cruising)
- Long distances approach constant energy/meter (mostly cruising)
- Wait energy unchanged (still P_idle × time / 1000)
