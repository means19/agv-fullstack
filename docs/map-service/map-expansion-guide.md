# Map Expansion Guide - Complete Warehouse Layout

## Current Map (11 nodes, 24 edges)
```
DEPOT-01      CA-01 ━━━ CA-02 ━━━ CA-03      DEPOT-02
  🟢           🔵       🔵       🔵          🟢
              ┃         ┃         ┃
              CA-04 ━━━ CA-05 ━━━ CA-06
              🔵       🔵       🔵
              ┃         ┃         ┃
STATION-A           STATION-B  STATION-C
  🟠                 🟠         🟠
```

## Expanded Map Design (30+ nodes, 60+ edges)

### Layout Concept: Realistic Warehouse
```
DEPOT-01   CA-01 ━ CA-02 ━ CA-03 ━ CA-04 ━ CA-05   DEPOT-02
  🟢         🔵     🔵     🔵     🔵     🔵         🟢
            ┃       ┃       ┃       ┃       ┃
         CA-06 ━ CA-07 ━ CA-08 ━ CA-09 ━ CA-10
            🔵     🔵     🔵     🔵     🔵
            ┃       ┃       ┃       ┃       ┃
         CA-11 ━ CA-12 ━ CA-13 ━ CA-14 ━ CA-15
            🔵     🔵     🔵     🔵     🔵
            ┃       ┃       ┃       ┃       ┃
         CA-16 ━ CA-17 ━ CA-18 ━ CA-19 ━ CA-20
            🔵     🔵     🔵     🔵     🔵
            ┃       ┃       ┃       ┃       ┃
STATION-A        STATION-B      STATION-C      STATION-D
  🟠              🟠            🟠            🟠
```

## Steps to Expand

### Option 1: Edit CSV Files Directly

**1. Edit `data/nodes.csv`:**
- Add more CA nodes (CA-07 to CA-20)
- Add more stations (STATION-D, STATION-E, etc.)
- Maintain grid spacing: 200px horizontal, 200px vertical

**2. Edit `data/edges.csv`:**
- Add horizontal connections (CA-01 ↔ CA-02, etc.)
- Add vertical connections (CA-01 ↔ CA-06, etc.)
- Keep bidirectional (both directions)

**3. Import to database:**
```bash
docker compose exec server python manage.py import_map
```

### Option 2: Use Python Script to Generate

Create `generate_map.py` to generate large grids automatically.

## Example: 5x4 Grid (20 CA nodes)

### Nodes (27 total):
- 20 Control Areas (CA-01 to CA-20) in 5x4 grid
- 2 Depots (DEPOT-01, DEPOT-02) at top corners
- 5 Stations (STATION-A to STATION-E) at bottom

### Edges (80+ total):
- Horizontal: 15 connections × 2 directions = 30 edges
- Vertical: 12 connections × 2 directions = 24 edges
- Depot connections: 2 × 2 = 4 edges
- Station connections: 5 × 2 = 10 edges
- **Total: 68 edges**

## Coordinate System

### Grid Spacing:
- **X spacing**: 200 pixels
- **Y spacing**: 200 pixels
- **Start point**: (100, 100)

### Formula:
```
CA at row i, col j:
  name: CA-{(i-1)*cols + j}
  pos_x: 100 + (j-1) * 200
  pos_y: 100 + (i-1) * 200
```

### Example 5x4 Grid:
```
Row 1: CA-01(100,100), CA-02(300,100), CA-03(500,100), CA-04(700,100), CA-05(900,100)
Row 2: CA-06(100,300), CA-07(300,300), CA-08(500,300), CA-09(700,300), CA-10(900,300)
Row 3: CA-11(100,500), CA-12(300,500), CA-13(500,500), CA-14(700,500), CA-15(900,500)
Row 4: CA-16(100,700), CA-17(300,700), CA-18(500,700), CA-19(700,700), CA-20(900,700)
```

## Distance Calculation

### Standard Distances:
- **Horizontal CA-CA**: 200m
- **Vertical CA-CA**: 200m
- **CA to DEPOT/STATION**: ~70m (diagonal) or 100m (straight)

### Time Calculation:
```
base_time_sec = distance_m / 2.0  (assuming 2 m/s base speed)
```

## Quick Start: Generate Maps

### Map 4 rows × 5 columns (20 CA nodes)
```
python generate_warehouse_map.py --rows 4 --cols 5 --depots 2 --stations 5
```
### Map 6 rows × 8 columns (48 CA nodes) - Warehouse lớn
```
python generate_warehouse_map.py --rows 6 --cols 8 --depots 4 --stations 8
```
### Map 10 rows × 12 columns (120 CA nodes) - Mega warehouse
```
python generate_warehouse_map.py --rows 10 --cols 12 --depots 4 --stations 10
```