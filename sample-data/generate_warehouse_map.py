"""
Map Generator Script
Automatically generates nodes.csv and edges.csv for AGV map

Usage:
    python generate_warehouse_map.py --rows 4 --cols 5 --depots 2 --stations 5
    
This will create:
    - data/nodes_generated.csv (27 nodes: 20 CA + 2 DEPOT + 5 STATION)
    - data/edges_generated.csv (68 bidirectional edges)
"""

import argparse
import csv
import os


def generate_map(rows: int, cols: int, num_depots: int, num_stations: int):
    """
    Generate warehouse map with grid layout
    
    Args:
        rows: Number of rows in CA grid
        cols: Number of columns in CA grid
        num_depots: Number of depot nodes
        num_stations: Number of station nodes
    """
    
    # Configuration
    X_SPACING = 200  # Horizontal spacing in pixels
    Y_SPACING = 200  # Vertical spacing in pixels
    START_X = 100    # Starting X coordinate
    START_Y = 100    # Starting Y coordinate
    
    DEPOT_OFFSET_X = -50   # Depot X offset from edge
    DEPOT_OFFSET_Y = -50   # Depot Y offset from edge
    STATION_OFFSET_Y = 50  # Station Y offset below last row
    
    HORIZONTAL_DISTANCE = 200  # Distance between horizontally adjacent CAs (meters)
    VERTICAL_DISTANCE = 200    # Distance between vertically adjacent CAs (meters)
    DEPOT_DISTANCE = 70        # Distance from DEPOT to nearest CA (meters)
    STATION_DISTANCE = 70      # Distance from CA to STATION (meters)
    
    BASE_SPEED = 2.0  # Base speed for time calculation (m/s)
    
    nodes = []
    edges = []
    
    # ========== Generate CA Nodes (Grid) ==========
    ca_nodes = {}
    for row in range(rows):
        for col in range(cols):
            ca_num = row * cols + col + 1
            ca_name = f"CA-{ca_num:02d}"
            pos_x = START_X + col * X_SPACING
            pos_y = START_Y + row * Y_SPACING
            
            nodes.append({
                'name': ca_name,
                'resource_type': 'CA',
                'pos_x': pos_x,
                'pos_y': pos_y
            })
            
            ca_nodes[(row, col)] = ca_name
    
    # ========== Generate DEPOT Nodes ==========
    depots = []
    if num_depots >= 1:
        # DEPOT-01: Top-left
        depots.append({
            'name': 'DEPOT-01',
            'resource_type': 'DEPOT',
            'pos_x': START_X + DEPOT_OFFSET_X,
            'pos_y': START_Y + DEPOT_OFFSET_Y
        })
    
    if num_depots >= 2:
        # DEPOT-02: Top-right
        depots.append({
            'name': 'DEPOT-02',
            'resource_type': 'DEPOT',
            'pos_x': START_X + (cols - 1) * X_SPACING - DEPOT_OFFSET_X,
            'pos_y': START_Y + DEPOT_OFFSET_Y
        })
    
    if num_depots >= 3:
        # DEPOT-03: Middle-left
        depots.append({
            'name': 'DEPOT-03',
            'resource_type': 'DEPOT',
            'pos_x': START_X + DEPOT_OFFSET_X,
            'pos_y': START_Y + (rows // 2) * Y_SPACING
        })
    
    if num_depots >= 4:
        # DEPOT-04: Middle-right
        depots.append({
            'name': 'DEPOT-04',
            'resource_type': 'DEPOT',
            'pos_x': START_X + (cols - 1) * X_SPACING - DEPOT_OFFSET_X,
            'pos_y': START_Y + (rows // 2) * Y_SPACING
        })
    
    nodes.extend(depots)
    
    # ========== Generate STATION Nodes ==========
    stations = []
    station_spacing = (cols - 1) * X_SPACING / max(num_stations - 1, 1)
    
    for i in range(num_stations):
        station_name = chr(65 + i)  # A, B, C, D, E...
        pos_x = START_X + i * station_spacing
        pos_y = START_Y + (rows - 1) * Y_SPACING + STATION_OFFSET_Y
        
        stations.append({
            'name': f'STATION-{station_name}',
            'resource_type': 'STATION',
            'pos_x': int(pos_x),
            'pos_y': pos_y
        })
    
    nodes.extend(stations)
    
    # ========== Generate Edges ==========
    
    # 1. Horizontal CA connections (within each row)
    for row in range(rows):
        for col in range(cols - 1):
            from_ca = ca_nodes[(row, col)]
            to_ca = ca_nodes[(row, col + 1)]
            
            # Forward direction
            edges.append({
                'name': f'LSA_{from_ca.replace("-", "")}_{to_ca.replace("-", "")}',
                'resource_type': 'LSA',
                'from_node': from_ca,
                'to_node': to_ca,
                'distance_m': HORIZONTAL_DISTANCE,
                'base_time_sec': HORIZONTAL_DISTANCE / BASE_SPEED
            })
            
            # Backward direction
            edges.append({
                'name': f'LSA_{to_ca.replace("-", "")}_{from_ca.replace("-", "")}',
                'resource_type': 'LSA',
                'from_node': to_ca,
                'to_node': from_ca,
                'distance_m': HORIZONTAL_DISTANCE,
                'base_time_sec': HORIZONTAL_DISTANCE / BASE_SPEED
            })
    
    # 2. Vertical CA connections (between rows)
    for row in range(rows - 1):
        for col in range(cols):
            from_ca = ca_nodes[(row, col)]
            to_ca = ca_nodes[(row + 1, col)]
            
            # Forward direction
            edges.append({
                'name': f'LSA_{from_ca.replace("-", "")}_{to_ca.replace("-", "")}',
                'resource_type': 'LSA',
                'from_node': from_ca,
                'to_node': to_ca,
                'distance_m': VERTICAL_DISTANCE,
                'base_time_sec': VERTICAL_DISTANCE / BASE_SPEED
            })
            
            # Backward direction
            edges.append({
                'name': f'LSA_{to_ca.replace("-", "")}_{from_ca.replace("-", "")}',
                'resource_type': 'LSA',
                'from_node': to_ca,
                'to_node': from_ca,
                'distance_m': VERTICAL_DISTANCE,
                'base_time_sec': VERTICAL_DISTANCE / BASE_SPEED
            })
    
    # 3. DEPOT connections
    if num_depots >= 1:
        # DEPOT-01 to CA-01 (top-left)
        from_node = 'DEPOT-01'
        to_node = ca_nodes[(0, 0)]
        
        edges.append({
            'name': f'LSA_D01_{to_node.replace("-", "")}',
            'resource_type': 'LSA',
            'from_node': from_node,
            'to_node': to_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
        edges.append({
            'name': f'LSA_{to_node.replace("-", "")}_D01',
            'resource_type': 'LSA',
            'from_node': to_node,
            'to_node': from_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
    
    if num_depots >= 2:
        # DEPOT-02 to top-right CA
        from_node = 'DEPOT-02'
        to_node = ca_nodes[(0, cols - 1)]
        
        edges.append({
            'name': f'LSA_D02_{to_node.replace("-", "")}',
            'resource_type': 'LSA',
            'from_node': from_node,
            'to_node': to_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
        edges.append({
            'name': f'LSA_{to_node.replace("-", "")}_D02',
            'resource_type': 'LSA',
            'from_node': to_node,
            'to_node': from_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
    
    if num_depots >= 3:
        # DEPOT-03 to middle-left CA
        from_node = 'DEPOT-03'
        to_node = ca_nodes[(rows // 2, 0)]
        
        edges.append({
            'name': f'LSA_D03_{to_node.replace("-", "")}',
            'resource_type': 'LSA',
            'from_node': from_node,
            'to_node': to_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
        edges.append({
            'name': f'LSA_{to_node.replace("-", "")}_D03',
            'resource_type': 'LSA',
            'from_node': to_node,
            'to_node': from_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
    
    if num_depots >= 4:
        # DEPOT-04 to middle-right CA
        from_node = 'DEPOT-04'
        to_node = ca_nodes[(rows // 2, cols - 1)]
        
        edges.append({
            'name': f'LSA_D04_{to_node.replace("-", "")}',
            'resource_type': 'LSA',
            'from_node': from_node,
            'to_node': to_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
        edges.append({
            'name': f'LSA_{to_node.replace("-", "")}_D04',
            'resource_type': 'LSA',
            'from_node': to_node,
            'to_node': from_node,
            'distance_m': DEPOT_DISTANCE,
            'base_time_sec': DEPOT_DISTANCE / BASE_SPEED
        })
    
    # 4. STATION connections (connect to bottom row CAs)
    bottom_row_cas = [(rows - 1, col) for col in range(cols)]
    
    for i, station in enumerate(stations):
        # Find nearest CA in bottom row
        nearest_col = int(i * (cols - 1) / max(num_stations - 1, 1))
        nearest_ca = ca_nodes[(rows - 1, min(nearest_col, cols - 1))]
        
        station_code = station['name'].split('-')[1]  # A, B, C...
        
        edges.append({
            'name': f'LSA_{nearest_ca.replace("-", "")}_S{station_code}',
            'resource_type': 'LSA',
            'from_node': nearest_ca,
            'to_node': station['name'],
            'distance_m': STATION_DISTANCE,
            'base_time_sec': STATION_DISTANCE / BASE_SPEED
        })
        edges.append({
            'name': f'LSA_S{station_code}_{nearest_ca.replace("-", "")}',
            'resource_type': 'LSA',
            'from_node': station['name'],
            'to_node': nearest_ca,
            'distance_m': STATION_DISTANCE,
            'base_time_sec': STATION_DISTANCE / BASE_SPEED
        })
    
    return nodes, edges


def save_to_csv(nodes, edges, output_dir='data'):
    """Save nodes and edges to CSV files"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save nodes
    nodes_file = os.path.join(output_dir, 'nodes_generated.csv')
    with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'resource_type', 'pos_x', 'pos_y'])
        writer.writeheader()
        writer.writerows(nodes)
    
    print(f"✅ Created {nodes_file} with {len(nodes)} nodes")
    
    # Save edges
    edges_file = os.path.join(output_dir, 'edges_generated.csv')
    with open(edges_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'resource_type', 'from_node', 'to_node', 'distance_m', 'base_time_sec'])
        writer.writeheader()
        writer.writerows(edges)
    
    print(f"✅ Created {edges_file} with {len(edges)} edges")
    
    # Print summary
    print(f"\n📊 Map Summary:")
    print(f"   Total Nodes: {len(nodes)}")
    ca_count = sum(1 for n in nodes if n['resource_type'] == 'CA')
    depot_count = sum(1 for n in nodes if n['resource_type'] == 'DEPOT')
    station_count = sum(1 for n in nodes if n['resource_type'] == 'STATION')
    print(f"   - Control Areas: {ca_count}")
    print(f"   - Depots: {depot_count}")
    print(f"   - Stations: {station_count}")
    print(f"   Total Edges: {len(edges)}")
    print(f"\n📁 Files created in '{output_dir}/' directory")
    print(f"\n🚀 Next steps:")
    print(f"   1. Review the generated CSV files")
    print(f"   2. Rename to nodes.csv and edges.csv (or keep separate)")
    print(f"   3. Copy to Docker container:")
    print(f"      docker compose cp data/nodes_generated.csv server:/app/data/nodes.csv")
    print(f"      docker compose cp data/edges_generated.csv server:/app/data/edges.csv")
    print(f"   4. Import to database:")
    print(f"      docker compose exec server python manage.py import_map")


def main():
    parser = argparse.ArgumentParser(description='Generate AGV warehouse map')
    parser.add_argument('--rows', type=int, default=4, help='Number of rows in CA grid (default: 4)')
    parser.add_argument('--cols', type=int, default=5, help='Number of columns in CA grid (default: 5)')
    parser.add_argument('--depots', type=int, default=2, help='Number of depot nodes (default: 2)')
    parser.add_argument('--stations', type=int, default=5, help='Number of station nodes (default: 5)')
    parser.add_argument('--output', type=str, default='data', help='Output directory (default: data)')
    
    args = parser.parse_args()
    
    print(f"🏭 Generating warehouse map...")
    print(f"   Grid size: {args.rows} rows × {args.cols} columns")
    print(f"   Depots: {args.depots}")
    print(f"   Stations: {args.stations}")
    print()
    
    nodes, edges = generate_map(args.rows, args.cols, args.depots, args.stations)
    save_to_csv(nodes, edges, args.output)


if __name__ == '__main__':
    main()
