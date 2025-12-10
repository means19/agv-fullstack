# Map Service Documentation

Complete documentation for the AGV Map Service system.

---

## 📚 Documentation Files

### 1. [map-implementation-completed.md](./map-implementation-completed.md)
**Purpose**: Original implementation guide using HYBRID approach (ResourceAgent extension)

**Content**:
- Database model extension (ResourceAgent with CA, LSA, DEPOT, STATION)
- Sample data structure
- MapService singleton with NetworkX
- REST API endpoints (layout, pathfinding)
- Deployment steps
- Architecture decisions

**Status**: ✅ Implementation completed (Nov 28, 2025)

**Use When**: Understanding the original hybrid map system with ResourceAgent

---

### 2. [map-expansion-guide.md](./map-expansion-guide.md)
**Purpose**: Guide for expanding map to larger warehouse layouts

**Content**:
- Current 11-node map layout
- Expanded map design (30+ nodes, 60+ edges)
- Grid generation formulas
- CSV editing instructions
- Quick start commands for different map sizes

**Status**: ✅ Reference guide

**Use When**: Need to scale map for larger warehouse simulations

---

### 3. [map-implementation-test-results.md](./map-implementation-test-results.md)
**Purpose**: Test results and verification of implemented map system

**Content**:
- Migration test results
- API endpoint tests (layout, pathfinding)
- Error handling validation
- Performance metrics
- Technology stack details

**Status**: ✅ All tests passing (Nov 8, 2025)

**Use When**: Verifying map system functionality or debugging issues

---

### 4. [map-refactoring-complete.md](./map-refactoring-complete.md) ⭐ NEW
**Purpose**: Clean architecture refactoring documentation

**Content**:
- Refactored architecture (service layer pattern)
- Design patterns applied (Manager, Service Layer, Exception Hierarchy)
- Code organization improvements
- API endpoint updates
- Migration guide from old to new code
- Usage examples

**Status**: ✅ Refactoring completed (Dec 2, 2025)

**Use When**: Understanding the refactored codebase or maintaining map service

---

## 🗺️ Map Service Overview

### Two Map Systems

#### 1. **Legacy System** (map_data app)
- Connection/Direction models (integer-based nodes)
- CSV import/export
- Simple grid structure
- **Status**: Refactored with clean architecture

#### 2. **Hybrid System** (agv_data app)
- ResourceAgent model (CA, LSA, DEPOT, STATION)
- NetworkX graph algorithms
- Advanced pathfinding (Dijkstra)
- **Status**: Production ready

### Current Recommendation
Use **Hybrid System** (ResourceAgent) for new features:
- More flexible (nodes have names, types, positions)
- Better integration with reservation system
- Built-in pathfinding algorithms
- Visualization-ready (pos_x, pos_y)

---

## 🚀 Quick Start

### Import Map Data (Legacy System)
```bash
# Via API
curl -X POST http://localhost:8000/api/map/import-connections/ \
  --data-binary @sample-data/map-connection-and-distance.csv

curl -X POST http://localhost:8000/api/map/import-directions/ \
  --data-binary @sample-data/map-direction.csv
```

### Import Map Data (Hybrid System)
```bash
# Via management command
docker exec django_app python manage.py import_map
```

### Get Map Layout
```bash
# Legacy system
curl http://localhost:8000/api/map/get/

# Hybrid system
curl http://localhost:8000/api/agvs/map/layout/
```

### Calculate Path
```bash
# Hybrid system only
curl "http://localhost:8000/api/agvs/map/path/?start=CA-01&end=STATION-A&speed=1.5"
```

---

## 📁 File Structure

```
docs/map-service/
├── README.md                              # This file
├── map-implementation-completed.md        # Original implementation guide
├── map-expansion-guide.md                 # Map scaling guide
├── map-implementation-test-results.md     # Test results
└── map-refactoring-complete.md            # Refactoring documentation

agv_server/map_data/                       # Legacy map service (refactored)
├── models.py                              # Connection, Direction models
├── services/
│   ├── import_service.py                  # CSV import logic
│   ├── query_service.py                   # Data queries
│   └── validation_service.py              # Validation logic
├── views.py                               # API endpoints
├── exceptions.py                          # Custom exceptions
└── constants.py                           # Constants

agv_server/agv_data/                       # Hybrid system
├── models.py                              # ResourceAgent, Booking
├── services.py                            # MapService (NetworkX)
└── views.py                               # Map layout, pathfinding APIs

sample-data/
├── nodes.csv                              # Hybrid system nodes
├── edges.csv                              # Hybrid system edges
├── map-connection-and-distance.csv        # Legacy connections
└── map-direction.csv                      # Legacy directions
```

---

## 🔧 Maintenance

### Check System Status
```bash
# Django checks
docker exec django_app python manage.py check map_data

# Get statistics
curl http://localhost:8000/api/map/statistics/
```

### Reset Map Data
```bash
# Legacy system
curl -X POST http://localhost:8000/api/map/delete/

# Hybrid system - via Django shell
docker exec -it django_app python manage.py shell
>>> from agv_data.models import ResourceAgent
>>> ResourceAgent.objects.all().delete()
```

### Common Issues

**Issue**: "No map data available"
```bash
# Solution: Import map data
docker exec django_app python manage.py import_map
```

**Issue**: "No path found"
```bash
# Solution: Check if nodes exist and are ONLINE
curl http://localhost:8000/api/agvs/map/layout/
```

---

## 📊 Map Data Format

### Legacy System (CSV)
**Connections** (N×N matrix):
```
1,200,10000,...
200,1,200,...
10000,200,1,...
```
- Value = distance in meters
- 10000 = no connection

**Directions** (N×N matrix):
```
1,2,10000,...
4,1,2,...
10000,4,1,...
```
- 1=North, 2=East, 3=South, 4=West
- 10000 = no direction

### Hybrid System (CSV)
**Nodes**:
```csv
name,resource_type,pos_x,pos_y,status
CA-01,CA,100,100,ONLINE
DEPOT-01,DEPOT,50,50,ONLINE
STATION-A,STATION,50,350,ONLINE
```

**Edges**:
```csv
name,resource_type,from_ca,to_ca,distance_m,base_time_sec,status
LSA_CA01_CA02,LSA,CA-01,CA-02,200,100,ONLINE
```

---

## 🎯 Best Practices

1. **Use Hybrid System** for new features (ResourceAgent)
2. **Keep Legacy System** for backward compatibility
3. **Test After Changes**: Run full test suite
4. **Document Changes**: Update relevant .md files
5. **Version Control**: Commit with clear messages

---

## 📝 Changelog

### Dec 2, 2025 - Refactoring Complete
- ✅ Refactored map_data app with clean architecture
- ✅ Added service layer (Import, Query, Validation)
- ✅ Converted to class-based views (DRF)
- ✅ Added custom model managers
- ✅ Created exception hierarchy
- ✅ Added statistics endpoint

### Nov 28, 2025 - DSPA Removal
- ✅ Removed deprecated DSPA algorithms
- ✅ Simplified MQTT/Godot handlers
- ✅ Retained SSI-DMAS-ET auction system

### Nov 8, 2025 - Hybrid System Complete
- ✅ ResourceAgent model extended
- ✅ NetworkX integration
- ✅ Pathfinding APIs
- ✅ Sample data imported

---

## 🔗 Related Documentation

- [Database Schema](../database-schema.md)
- [System Structure](../web-app-services.md)
- [Local Development](../local-dev.md)
- [Reservation Table](../reservation_table.md)

---

**Last Updated**: December 2, 2025  
**Maintained By**: Development Team  
**Status**: ✅ Production Ready
