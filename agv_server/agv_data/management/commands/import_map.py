"""
Django management command to import map data from CSV files.
Loads nodes (CA, DEPOT, STATION) and edges (LSA) into ResourceAgent model.
"""

import csv
import os
from django.core.management.base import BaseCommand
from agv_data.models import ResourceAgent


class Command(BaseCommand):
    help = 'Import map data from nodes.csv and edges.csv'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting map import...'))
        
        # Get paths to CSV files (in Docker container: /app is the project root)
        # Try multiple possible paths
        possible_roots = [
            '/app',  # Docker container
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),  # Local development
        ]
        
        nodes_path = None
        edges_path = None
        
        for root in possible_roots:
            test_nodes = os.path.join(root, 'data', 'nodes.csv')
            test_edges = os.path.join(root, 'data', 'edges.csv')
            if os.path.exists(test_nodes) and os.path.exists(test_edges):
                nodes_path = test_nodes
                edges_path = test_edges
                break
        
        # Check if files exist
        if not nodes_path or not os.path.exists(nodes_path):
            self.stdout.write(self.style.ERROR(f'nodes.csv not found. Tried paths:'))
            for root in possible_roots:
                self.stdout.write(f'  - {os.path.join(root, "data", "nodes.csv")}')
            return
        if not edges_path or not os.path.exists(edges_path):
            self.stdout.write(self.style.ERROR(f'edges.csv not found at {edges_path}'))
            return
        
        # Clear existing data
        self.stdout.write('Clearing existing ResourceAgent data...')
        ResourceAgent.objects.all().delete()
        
        # Import nodes
        self.stdout.write('Importing nodes from nodes.csv...')
        nodes_created = 0
        node_cache = {}  # Cache for name -> object mapping
        
        with open(nodes_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                node = ResourceAgent.objects.create(
                    name=row['name'],
                    resource_type=row['resource_type'],
                    pos_x=int(row['pos_x']),
                    pos_y=int(row['pos_y']),
                    status='ONLINE'
                )
                node_cache[row['name']] = node
                nodes_created += 1
                self.stdout.write(f'  Created {row["resource_type"]}: {row["name"]}')
        
        self.stdout.write(self.style.SUCCESS(f'Created {nodes_created} nodes'))
        
        # Import edges
        self.stdout.write('Importing edges from edges.csv...')
        edges_created = 0
        edges_skipped = 0
        
        with open(edges_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                from_node_name = row['from_node']
                to_node_name = row['to_node']
                
                # Check if both nodes exist in cache
                if from_node_name not in node_cache:
                    self.stdout.write(self.style.WARNING(f'  Skipping {row["name"]}: from_node "{from_node_name}" not found'))
                    edges_skipped += 1
                    continue
                if to_node_name not in node_cache:
                    self.stdout.write(self.style.WARNING(f'  Skipping {row["name"]}: to_node "{to_node_name}" not found'))
                    edges_skipped += 1
                    continue
                
                # Create edge
                edge = ResourceAgent.objects.create(
                    name=row['name'],
                    resource_type='LSA',
                    status='ONLINE',
                    from_ca=node_cache[from_node_name],
                    to_ca=node_cache[to_node_name],
                    distance_m=float(row['distance_m']),
                    base_time_sec=float(row['base_time_sec'])
                )
                edges_created += 1
                self.stdout.write(f'  Created LSA: {row["name"]} ({from_node_name} → {to_node_name}, {row["distance_m"]}m)')
        
        self.stdout.write(self.style.SUCCESS(f'Created {edges_created} edges'))
        if edges_skipped > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {edges_skipped} edges (missing nodes)'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS(f'Map import complete!'))
        self.stdout.write(self.style.SUCCESS(f'Total nodes: {nodes_created}'))
        self.stdout.write(self.style.SUCCESS(f'Total edges: {edges_created}'))
        self.stdout.write(self.style.SUCCESS('='*60))
