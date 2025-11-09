# AGV Fullstack - Documentation Index

📚 **Complete Documentation for AGV DMAS-ET System**

**Last Updated:** November 9, 2025  
**System Version:** 1.2

---

## 🎯 Start Here

### New to the project?
👉 **[DMAS-ET-OVERVIEW.md](./DMAS-ET-OVERVIEW.md)** - System architecture and overview

### Need to test something?
👉 **[local-dev.md](./local-dev.md)** - Development environment setup

### Looking for specific component?
See [Documentation by Component](#-documentation-by-component) below

---

## 📖 Core Documentation

### 1. 🏗️ System Overview
**[DMAS-ET-OVERVIEW.md](./DMAS-ET-OVERVIEW.md)**
- Complete system architecture
- All 3 phases (Auction, Exploring Ant, Intention Ant)
- Implementation status
- Development roadmap
- Key concepts and algorithms

**👥 For:** Everyone (start here!)

---

### 2. 🔧 Development Setup
**[local-dev.md](./local-dev.md)**
- Docker setup
- Environment variables
- Running services
- Debugging guide

**👥 For:** Developers

---

### 3. 🗄️ Database
**[database-schema.md](./database-schema.md)**
- All database models
- Relationships
- Field descriptions

**👥 For:** Backend developers, database admins

---

### 4. 🌐 System Architecture
**[web-app-services.md](./web-app-services.md)**
- Service architecture
- Frontend-backend communication
- WebSocket protocols

**👥 For:** System architects

---

## 🧩 Documentation by Component

### ✅ Phase 1: Auction System (COMPLETE)
**Folder:** [`auction-logic/`](./auction-logic/)

**Key Files:**
- **[README.md](./auction-logic/README.md)** - Auction docs index
- **[auction-bidding-quickstart.md](./auction-logic/auction-bidding-quickstart.md)** - Quick start & testing
- **[auction-bidding-implementation.md](./auction-logic/auction-bidding-implementation.md)** - Detailed implementation
- **[integration-verification.md](./auction-logic/integration-verification.md)** - Integration verification
- **[verification-marginal-cost.md](./auction-logic/verification-marginal-cost.md)** - Algorithm correctness
- **[auction-changelog.md](./auction-logic/auction-changelog.md)** - Version history

**Status:** 🟢 COMPLETED

**What it does:**
- Allocates tasks to AGVs through competitive bidding
- Dynamic baseline normalization
- Hybrid MiniSum/MiniMax objective
- Support for idle and busy AGVs

---

### ✅ Phase 2: Exploring Ant (DMAS-ET) (COMPLETE)
**Folder:** [`exploring-ants/`](./exploring-ants/)

**Key Files:**
- **[agv-agent-exploring-ant.md](./exploring-ants/agv-agent-exploring-ant.md)** - Algorithm details
- **[agv-agent-implementation-summary.md](./exploring-ants/agv-agent-implementation-summary.md)** - Summary
- **[agv-agent-quickstart.md](./exploring-ants/agv-agent-quickstart.md)** - Quick start

**Status:** 🟢 COMPLETED

**What it does:**
- Simulates AGV journey on planned route
- Queries reservation table for conflicts
- Calculates energy and Total Flow Time (TFT)
- Returns raw costs for bidding layer

---

### ✅ Reservation Table (COMPLETE)
**Folder:** [`reservation-table/`](./reservation-table/)

**Key Files:**
- **[reservation-table.md](./reservation-table/reservation-table.md)** - API documentation
- **[reservation-table-implementation-summary.md](./reservation-table/reservation-table-implementation-summary.md)** - Summary
- **[reservation-table-quickstart.md](./reservation-table/reservation-table-quickstart.md)** - Quick start

**Status:** 🟢 COMPLETED

**What it does:**
- Manages time-based resource reservations
- Query API (exploring phase)
- Booking API (intention phase)
- Transaction isolation for atomicity

---

### ✅ Map Service (COMPLETE)
**Folder:** [`map-service/`](./map-service/)

**Key Files:**
- **[map-implementation-completed.md](./map-service/map-implementation-completed.md)** - Implementation
- **[map-implementation-test-results.md](./map-service/map-implementation-test-results.md)** - Test results
- **[map-expansion-guide.md](./map-service/map-expansion-guide.md)** - Expansion guide

**Status:** 🟢 COMPLETED

**What it does:**
- Graph-based pathfinding (Dijkstra)
- NetworkX graph from ResourceAgent database
- Returns RouteStep with distances and times
- 248 ResourceAgent records (48 CA nodes, 188 LSA edges)

---

### ⏳ Intention Ant (PENDING)
**Status:** 🔴 Not Started

**Will do:**
- Book actual time slot reservations
- Handle booking conflicts (409 → replan)
- Transaction rollback on failure
- Update AGV schedule after booking

**Next Steps:** See [DMAS-ET-OVERVIEW.md - Roadmap](./DMAS-ET-OVERVIEW.md#-development-roadmap)

---

## 📋 Reference Documents

### Algorithm Theory
**[tft-dynamic-normalization.md](./tft-dynamic-normalization.md)**
- Total Flow Time (TFT) vs Sum of Tardiness (SOT)
- Dynamic baseline normalization theory
- Hybrid objective (MiniSum + MiniMax)
- Mathematical formulas

---

### Communication Protocols
**[frontend-backend-websocket.md](./frontend-backend-websocket.md)**
- WebSocket message format
- Real-time updates

**[websocket-protocol-explanation.md](./websocket-protocol-explanation.md)**
- Detailed protocol specs

**[agv-server-mqtt.md](./agv-server-mqtt.md)**
- MQTT communication with AGVs
- Data frame format

**[data-frame-CRC.md](./data-frame-CRC.md)**
- CRC calculation for data frames

---

### Bug Fixes & Updates
**[journey-phase-implementation.md](./journey-phase-implementation.md)**
- Journey phase logic

**[journey-phase-changes-summary.md](./journey-phase-changes-summary.md)**
- Journey phase changes

**[critical-order-completion-fix.md](./critical-order-completion-fix.md)**
- Order completion bug fix

**[workstation-transition-fix.md](./workstation-transition-fix.md)**
- Workstation transition bug fix

**[spare-flag-fix.md](./spare-flag-fix.md)**
- Spare flag bug fix

**[spare-flag-logic-fix.md](./spare-flag-logic-fix.md)**
- Spare flag logic improvements

---

### Redis
**[redisCommand.md](./redisCommand.md)**
- Redis commands reference

---

## 🗺️ Documentation Structure

```
docs/
├── README.md ⭐ (THIS FILE)
│   └── Documentation index
│
├── DMAS-ET-OVERVIEW.md ⭐ START HERE
│   └── Complete system overview
│
├── auction-logic/ ✅ Phase 1
│   ├── README.md
│   ├── auction-bidding-quickstart.md
│   ├── auction-bidding-implementation.md
│   ├── INTEGRATION_VERIFICATION.md
│   ├── VERIFICATION_MARGINAL_COST.md
│   └── CHANGELOG.md
│
├── exploring-ants/ ✅ Phase 2
│   ├── agv-agent-exploring-ant.md
│   ├── agv-agent-implementation-summary.md
│   └── agv-agent-quickstart.md
│
├── reservation-table/ ✅ Infrastructure
│   ├── reservation-table.md
│   ├── reservation-table-implementation-summary.md
│   └── reservation-table-quickstart.md
│
├── map-service/ ✅ Infrastructure
│   ├── map-implementation-completed.md
│   ├── map-implementation-test-results.md
│   └── map-expansion-guide.md
│
├── tft-dynamic-normalization.md 📚 Theory
├── database-schema.md 📚 Reference
├── web-app-services.md 📚 Reference
├── local-dev.md 🛠️ Setup
├── frontend-backend-websocket.md 📡 Protocol
├── websocket-protocol-explanation.md 📡 Protocol
├── agv-server-mqtt.md 📡 Protocol
├── data-frame-CRC.md 📡 Protocol
├── redisCommand.md 🛠️ Reference
│
└── [Bug fixes & updates] 🐛
    ├── journey-phase-implementation.md
    ├── journey-phase-changes-summary.md
    ├── critical-order-completion-fix.md
    ├── workstation-transition-fix.md
    ├── spare-flag-fix.md
    └── spare-flag-logic-fix.md
```

---

## 🎯 Quick Find

### I want to...

**Understand the whole system**
→ [DMAS-ET-OVERVIEW.md](./DMAS-ET-OVERVIEW.md)

**Set up development environment**
→ [local-dev.md](./local-dev.md)

**Test the auction system**
→ [auction-logic/auction-bidding-quickstart.md](./auction-logic/auction-bidding-quickstart.md)

**Understand how bidding works**
→ [auction-logic/auction-bidding-implementation.md](./auction-logic/auction-bidding-implementation.md)

**Understand marginal cost calculation**
→ [auction-logic/verification-marginal-cost.md](./auction-logic/verification-marginal-cost.md)

**Understand DMAS-ET algorithm**
→ [exploring-ants/agv-agent-exploring-ant.md](./exploring-ants/agv-agent-exploring-ant.md)

**Understand reservation table**
→ [reservation-table/reservation-table.md](./reservation-table/reservation-table.md)

**Understand map/pathfinding**
→ [map-service/map-implementation-completed.md](./map-service/map-implementation-completed.md)

**See what's implemented**
→ [DMAS-ET-OVERVIEW.md - Implementation Status](./DMAS-ET-OVERVIEW.md#-implementation-status)

**See what's next**
→ [DMAS-ET-OVERVIEW.md - Roadmap](./DMAS-ET-OVERVIEW.md#-development-roadmap)

**Check database models**
→ [database-schema.md](./database-schema.md)

**Understand TFT metric**
→ [tft-dynamic-normalization.md](./tft-dynamic-normalization.md)

---

## 📊 System Status

| Component | Status | Documentation | Tests |
|-----------|--------|---------------|-------|
| **Auction System** | 🟢 Complete | ✅ Full | ✅ 6/6 passing |
| **Exploring Ant (DMAS-ET)** | 🟢 Complete | ✅ Full | ✅ Passing |
| **Reservation Table** | 🟢 Complete | ✅ Full | ✅ Passing |
| **Map Service** | 🟢 Complete | ✅ Full | ✅ Passing |
| **Intention Ant** | 🔴 Not Started | ⏳ Pending | ⏳ Pending |
| **Task Execution** | 🔴 Not Started | ⏳ Pending | ⏳ Pending |

**Overall:** Phase 1 & 2 Complete, Phase 3 Pending

---

## 🚀 Getting Started

### 1. Understand the System
```bash
# Read the overview
Start with: DMAS-ET-OVERVIEW.md
```

### 2. Set Up Environment
```bash
# Follow setup guide
Read: local-dev.md
Run: ./start-dev.ps1
```

### 3. Test Components
```bash
# Test auction system
docker compose exec server python test_auction_system.py

# Test with samples
docker compose exec server python sample-data/sample_test_1_idle_agvs.py
```

### 4. Explore Code
```bash
# Key files to read:
agv_server/agv_services/auctioneer_service.py
agv_server/agv_services/bidding_service.py
agv_server/agv_services/task_manager.py
agv_server/agv_data/agv_agent.py
agv_server/agv_data/services.py (MapService)
```

---

## 🤝 Contributing

### When adding features:
1. Update relevant component docs
2. Update [DMAS-ET-OVERVIEW.md](./DMAS-ET-OVERVIEW.md) implementation status
3. Add tests
4. Update this README if new major component

### When fixing bugs:
1. Document fix in component's docs
2. Update CHANGELOG.md in relevant folder
3. Add regression test

---

## 📞 Support

### For Questions:
1. Check this index
2. Read [DMAS-ET-OVERVIEW.md](./DMAS-ET-OVERVIEW.md)
3. Check component-specific docs
4. Review test files for usage examples

### For Issues:
1. Check bug fix docs
2. Check CHANGELOG.md files
3. Run tests to verify setup

---

**Last Review:** November 9, 2025  
**Next Review:** After Phase 3 (Intention Ant) completion

---

## 📄 Legend

- 🟢 **Complete** - Fully implemented and tested
- 🔴 **Not Started** - Planned but not yet implemented
- ⏳ **Pending** - Waiting for dependencies or next phase
- ✅ **Verified** - Tested and verified
- 📚 **Reference** - Theoretical or reference material
- 🛠️ **Setup** - Development environment
- 📡 **Protocol** - Communication protocols
- 🐛 **Bug Fix** - Bug fix documentation

---
