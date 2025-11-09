# Auction System Documentation# Auction & Bidding System Documentation



📚 **SSI-DMAS-ET Auction System - Complete Documentation**📚 **Complete documentation for the SSI-DMAS-ET auction system implementation**



> Part of the larger [DMAS-ET System](../DMAS-ET-OVERVIEW.md)---



---## 📖 Documentation Index



## 📖 Quick Navigation### 1. **Quick Start**

📄 **[auction-bidding-quickstart.md](./auction-bidding-quickstart.md)**

| Document | Purpose | For Whom |- How to run tests

|----------|---------|----------|- Step-by-step examples

| **[Quick Start](./auction-bidding-quickstart.md)** | Run tests, examples | New users, testers |- Test data creation

| **[Implementation](./auction-bidding-implementation.md)** | Detailed code docs | Developers |- Testing with idle and busy AGVs

| **[Integration Verification](./INTEGRATION_VERIFICATION.md)** | Integration status | System architects |

| **[Marginal Cost Verification](./VERIFICATION_MARGINAL_COST.md)** | Algorithm correctness | Reviewers |**Use this if:** You want to quickly test the auction system

| **[Changelog](./CHANGELOG.md)** | Version history | All users |

---

---

### 2. **Implementation Summary**

## 🎯 What is the Auction System?📄 **[auction-bidding-implementation-summary.md](./auction-bidding-implementation-summary.md)**

- Executive summary of implementation

The **Auction System** is Phase 1 of the SSI-DMAS-ET algorithm that allocates tasks to AGVs through competitive bidding:- Architecture diagram

- Key algorithms (A & B)

1. **Order arrives** → System needs to assign to best AGV- Configuration parameters

2. **Auctioneer calculates baseline** → Reference cost for normalization- Example scenario with 3 AGVs

3. **All AGVs bid** → Each calculates their cost (marginal for busy, full for idle)- Next steps

4. **Winner selected** → AGV with lowest normalized bid wins

**Use this if:** You want a high-level overview of the system

---

---

## ✅ Implementation Status

### 3. **Detailed Implementation**

**Version:** 1.2  📄 **[auction-bidding-implementation.md](./auction-bidding-implementation.md)**

**Status:** 🟢 **PRODUCTION READY**  - Detailed component documentation

**Last Updated:** November 9, 2025- AuctioneerService implementation

- BiddingService implementation

### Components- TaskManager implementation

- ✅ **AuctioneerService** - Baseline calculation from parking node- Code examples and usage

- ✅ **BiddingService** - Marginal cost + dynamic normalization- Integration details

- ✅ **TaskManager** - Complete auction orchestration

**Use this if:** You want to understand the implementation details

### Features

- ✅ Dynamic baseline normalization (scale-free comparison)---

- ✅ Hybrid MiniSum/MiniMax objective (ε = 0.5)

- ✅ Idle AGV support (J1 = 0, route from current position)### 4. **Integration Verification** ✨ NEW

- ✅ Busy AGV support (J1 from remaining_path, marginal cost)📄 **[INTEGRATION_VERIFICATION.md](./INTEGRATION_VERIFICATION.md)**

- ✅ Direct route planning (no parking detour)- MapService integration (11 usages verified)

- ✅ MapService integration (Dijkstra pathfinding)- Reservation Table integration (14 usages verified)

- ✅ DMAS-ET integration (reservation table queries)- ResourceAgent integration

- Order Model integration

### Testing- Agv Model integration

- ✅ All core tests passing (3/3)- Integration architecture diagram

- ✅ All sample tests passing (3/3)- Test results verification

- ✅ Integration verified (MapService: 11 usages, DMAS-ET: 14 usages)

**Use this if:** You want to verify system integration

---

---

## 🔑 Key Algorithms

### 5. **Changelog** ✨ NEW

### Algorithm A: Baseline Calculation📄 **[CHANGELOG.md](./CHANGELOG.md)**

```- Version 1.1 changes

Input: Order (parking_node, storage_node, workstation_node)- Bug fixes documentation

- New features (busy AGV support)

1. route = [parking → storage] + [storage → workstation]- Migration guide

2. (E_baseline, TFT_baseline) = DMAS_ET_silent(route)- Performance impact analysis

3. Return baseline for normalization

```**Use this if:** You want to see what changed in the latest version



**Purpose:** Provides task-specific reference cost for fair bid comparison.---



---### 6. **Integration Status** ✨ NEW

📄 **[INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md)**

### Algorithm B: Bid Calculation- Quick integration status summary

```- Component-by-component verification

Input: AGV, Order, E_baseline, TFT_baseline- Latest test results

- Performance metrics

1. Calculate J1 (current schedule cost):- Verification checklist

   - IDLE: J1 = (0, 0)

   - BUSY: J1 = cost from remaining_path**Use this if:** You want a quick integration status overview



2. Create route for new task:---

   - IDLE: start from current_node

   - BUSY: start from completion_node### 7. **Final Summary** ✨ NEW

📄 **[FINAL_SUMMARY.md](./FINAL_SUMMARY.md)**

3. Calculate J2 (current + new):- Executive summary for stakeholders

   J2 = DMAS_ET_silent(route)- Complete implementation overview

- Integration status dashboard

4. Calculate marginal cost:- Success criteria verification

   marginal = J2 - J1- Production readiness checklist



5. Normalize by baseline:**Use this if:** You want a comprehensive project completion summary

   E_norm = E_marginal / E_baseline

   TFT_norm = TFT_marginal / TFT_baseline---



6. Calculate hybrid bid:## 🎯 Quick Navigation

   b_ms = K_ENERGY * E_norm + K_TIME * TFT_norm

   b_mm = K_ENERGY * E_norm_total + K_TIME * TFT_norm_total### For New Users

   b_final = ε * b_ms + (1-ε) * b_mm1. Start with [Quick Start](./auction-bidding-quickstart.md)

```2. Read [Implementation Summary](./auction-bidding-implementation-summary.md)

3. Check [Integration Verification](./INTEGRATION_VERIFICATION.md)

**Purpose:** Calculates fair, normalized bid that balances efficiency and fairness.

### For Developers

**Key Innovation:** Marginal cost (J2 - J1) enables "task chaining" - busy AGVs can win if nearby!1. Read [Detailed Implementation](./auction-bidding-implementation.md)

2. Check [Changelog](./CHANGELOG.md) for recent changes

---3. Review [Integration Verification](./INTEGRATION_VERIFICATION.md) for integration points



## 💡 Key Concepts### For System Architects

1. Read [Implementation Summary](./auction-bidding-implementation-summary.md)

### 1. Dynamic Baseline Normalization2. Review [Integration Verification](./INTEGRATION_VERIFICATION.md)

Normalizes bids by task-specific baseline → scale-free comparison3. Check [Changelog](./CHANGELOG.md) for version history

- Small task: baseline = 10 kJ → bid of 5 kJ = 0.5 (good!)

- Large task: baseline = 100 kJ → bid of 50 kJ = 0.5 (also good!)---



### 2. Marginal Cost (J2 - J1)## 🔑 Key Concepts

Calculates **additional** cost for new task → fair for busy AGVs

- Idle AGV: marginal = full task cost### SSI-DMAS-ET Algorithm

- Busy AGV near task: marginal = only extra cost (task chaining!)- **SSI**: Selective Scheduling with Intention

- **DMAS**: Dynamic Multi-Agent System

**See:** [VERIFICATION_MARGINAL_COST.md](./VERIFICATION_MARGINAL_COST.md)- **ET**: Energy and Time optimization



### 3. Hybrid Objective (ε)### Core Components

Balances efficiency (MiniSum) and fairness (MiniMax)1. **AuctioneerService**: Calculates baseline costs for normalization

- ε = 1.0 → Pure efficiency (favor shortest route)2. **BiddingService**: Calculates AGV bids with dynamic normalization

- ε = 0.0 → Pure fairness (favor least loaded AGV)3. **TaskManager**: Orchestrates complete auction process

- ε = 0.5 → Balanced (default)

### Key Features

---- ✅ Dynamic baseline normalization (scale-free bids)

- ✅ Hybrid MiniSum/MiniMax objective (efficiency + fairness)

## 🔧 Configuration- ✅ Support for idle and busy AGVs

- ✅ Direct route planning (no unnecessary detours)

```python- ✅ Integration with MapService (Dijkstra pathfinding)

# File: agv_data/agv_agent_constants.py- ✅ Integration with Reservation Table (conflict detection)



# Energy Model---

C_BASE = 0.05           # Base energy (kJ/m)

C_LOAD_COEFF = 0.002    # Load energy (kJ/(kg·m))## 🚀 System Status



# Cost Weights**Version:** 1.1

K_ENERGY = 0.5          # Energy importance**Status:** ✅ **PRODUCTION READY**

K_TIME = 0.5            # Time importance**Last Updated:** November 9, 2025



# Hybrid Objective### Integration Status

EPSILON = 0.5           # MiniSum vs MiniMax balance| Component | Status | Documentation |

|-----------|--------|---------------|

# System| MapService | ✅ Integrated | [Integration Verification](./INTEGRATION_VERIFICATION.md#1-mapservice-integration) |

MIN_DURATION_SEC = 1.0  # Minimum slot duration| Reservation Table | ✅ Integrated | [Integration Verification](./INTEGRATION_VERIFICATION.md#2-dmas_et-integration-reservation-table-access) |

DEFAULT_LOAD_KG = 100.0 # Default load weight| ResourceAgent | ✅ Integrated | [Integration Verification](./INTEGRATION_VERIFICATION.md#3-resourceagent-integration) |

```| Order Model | ✅ Integrated | [Integration Verification](./INTEGRATION_VERIFICATION.md#4-order-model-integration) |

| Agv Model | ✅ Integrated | [Integration Verification](./INTEGRATION_VERIFICATION.md#5-agv-model-integration) |

---

### Testing Status

## 🧪 Quick Test| Test | Status | Details |

|------|--------|---------|

```bash| Baseline Calculation | ✅ Passing | Baseline from parking node |

# Run complete test suite| Idle AGV Bidding | ✅ Passing | J1=0, route from current_node |

docker compose exec server python test_auction_system.py| Busy AGV Bidding | ✅ Passing | J1 from remaining_path, route from completion_node |

| Complete Auction | ✅ Passing | Winner selection correct |

# Run sample scenarios

docker compose exec server python sample-data/sample_test_1_idle_agvs.py---

docker compose exec server python sample-data/sample_test_2_mixed_agvs.py

docker compose exec server python sample-data/sample_test_3_multiple_orders.py## 📋 Implementation Checklist

```

### Completed ✅

**Expected:** All tests PASS ✅- [x] AuctioneerService with baseline from parking node

- [x] BiddingService with dynamic normalization

**Details:** See [auction-bidding-quickstart.md](./auction-bidding-quickstart.md)- [x] TaskManager for auction orchestration

- [x] Idle AGV support (J1=0, route from current_node)

---- [x] Busy AGV support (J1 from remaining_path, route from completion_node)

- [x] MapService integration (Dijkstra pathfinding)

## 🚀 Integration- [x] DMAS_ET integration (reservation table queries)

- [x] Node mapping fix (_node_number_to_name)

### Dependencies- [x] Duration fix (MIN_DURATION_SEC=1.0)

| Component | Purpose | Status |- [x] Direct route planning (no parking detour)

|-----------|---------|--------|- [x] Comprehensive test suite

| **MapService** | Dijkstra pathfinding | ✅ 11 usages |- [x] Complete documentation

| **DMAS-ET** | Cost calculation | ✅ 14 usages |

| **ResourceAgent** | Node lookups | ✅ Integrated |### Pending ⏳

| **Order Model** | Task specs | ✅ Integrated |- [ ] Integrate auction trigger on order arrival

| **Agv Model** | AGV state | ✅ Integrated |- [ ] Implement Intention Ant (task assignment)

- [ ] Implement book_slot_strict calls

**Full Details:** [INTEGRATION_VERIFICATION.md](./INTEGRATION_VERIFICATION.md)- [ ] Handle booking conflicts (409 → replan)

- [ ] TSP optimization for task insertion

---- [ ] Auction monitoring dashboard

- [ ] Auction history and analytics

## 📋 Next Steps (Pending)

---

- [ ] Integrate auction trigger on order arrival

- [ ] Implement Intention Ant (task assignment)## 🔧 Technical Specifications

- [ ] Implement book_slot_strict calls

- [ ] Handle booking conflicts (409 → replan)### Algorithm A: Baseline Calculation

- [ ] TSP optimization for multi-task insertion```

Input: Order (parking_node, storage_node, workstation_node)

**See Roadmap:** [../DMAS-ET-OVERVIEW.md](../DMAS-ET-OVERVIEW.md#-development-roadmap)Output: (E_baseline, TFT_baseline)



---1. Dijkstra(parking_node → storage_node) [empty]

2. Dijkstra(storage_node → workstation_node) [loaded]

## 📚 Related Documentation3. E_baseline = E1 + E2

4. TFT_baseline = T1 + T2

- **[../DMAS-ET-OVERVIEW.md](../DMAS-ET-OVERVIEW.md)** - System overview```

- **[../exploring-ants/](../exploring-ants/)** - DMAS-ET algorithm

- **[../reservation-table/](../reservation-table/)** - Reservation API### Algorithm B: Bid Calculation

- **[../tft-dynamic-normalization.md](../tft-dynamic-normalization.md)** - Theory```

Input: AGV, Order, E_baseline, TFT_baseline

---Output: b_final



## 🤝 Contributing1. IF AGV is IDLE:

     J1 = (0, 0)

When modifying auction system:     start = current_node

1. Update relevant docs   ELSE:

2. Run all tests     J1 = calculate_from_remaining_path()

3. Update CHANGELOG.md     start = completion_node

4. Verify integration

2. route = [start → storage → workstation]

---3. J2 = DMAS_ET_silent(route)

4. marginal = J2 - J1

**Last Updated:** November 9, 2025  5. normalize by baseline

**Version:** 1.2  6. b_final = ε*b_ms + (1-ε)*b_mm

**Status:** ✅ Production Ready```


### Configuration
```python
# Energy Constants
C_BASE = 0.05           # kJ/m
C_LOAD_COEFF = 0.002    # kJ/(kg·m)

# Cost Weights
K_ENERGY = 0.5
K_TIME = 0.5

# Hybrid Objective
EPSILON = 0.5

# System
MIN_DURATION_SEC = 1.0
DEFAULT_LOAD_KG = 100.0
```

---

## 📚 Related Documentation

### In Main Docs
- `database-schema.md`: Database models used by auction
- `reservation_table.md`: Reservation table API details
- `web-app-services.md`: System architecture overview

### External References
- SSI-DMAS-ET research paper (if available)
- Auction theory background
- Multi-agent systems literature

---

## 🤝 Contributing

When modifying the auction system:

1. **Update relevant documentation files**
2. **Run all tests** (`test_auction_system.py`)
3. **Update CHANGELOG.md** with your changes
4. **Verify integration** with MapService and Reservation Table
5. **Update this README** if adding new documentation

---

## 📞 Support

For questions or issues:
1. Check the documentation files above
2. Review the changelog for recent changes
3. Run the test suite to verify your setup
4. Check integration verification for system status

---

## 📄 License

Part of AGV Fullstack Project - Internal Documentation

---

**Last Updated:** November 9, 2025
**Documentation Version:** 1.1

