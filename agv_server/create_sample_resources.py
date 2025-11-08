"""
Script to create sample resources for Reservation Table testing
Run this with: docker-compose exec server python create_sample_resources.py
Or: python manage.py shell < create_sample_resources.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agv_server.settings')
django.setup()

from agv_data.models import ResourceAgent

def create_sample_resources():
    """Create sample Crossroad Agents and Logical Segment Agents"""
    
    print("Creating sample resources for Reservation Table...")
    print("-" * 60)
    
    # Create Crossroad Agents (CA)
    crossroads = [
        ("CA_01", "Crossroad at node 1"),
        ("CA_02", "Crossroad at node 2"),
        ("CA_03", "Crossroad at node 3"),
        ("CA_04", "Crossroad at node 4"),
        ("CA_05", "Crossroad at node 5"),
    ]
    
    print("\nCreating Crossroad Agents (CA)...")
    for name, desc in crossroads:
        ca, created = ResourceAgent.objects.get_or_create(
            name=name,
            defaults={'resource_type': 'CA'}
        )
        if created:
            print(f"  ✓ Created: {name} ({desc})")
        else:
            print(f"  ℹ Already exists: {name}")
    
    # Create Logical Segment Agents (LSA)
    segments = [
        ("LSA_01_02", "Segment between node 1 and 2"),
        ("LSA_02_03", "Segment between node 2 and 3"),
        ("LSA_03_04", "Segment between node 3 and 4"),
        ("LSA_04_05", "Segment between node 4 and 5"),
        ("LSA_05_01", "Segment between node 5 and 1"),
        ("LSA_01_06", "Segment between node 1 and 6"),
        ("LSA_06_07", "Segment between node 6 and 7"),
    ]
    
    print("\nCreating Logical Segment Agents (LSA)...")
    for name, desc in segments:
        lsa, created = ResourceAgent.objects.get_or_create(
            name=name,
            defaults={'resource_type': 'LSA'}
        )
        if created:
            print(f"  ✓ Created: {name} ({desc})")
        else:
            print(f"  ℹ Already exists: {name}")
    
    print("\n" + "-" * 60)
    print("Summary:")
    ca_count = ResourceAgent.objects.filter(resource_type='CA').count()
    lsa_count = ResourceAgent.objects.filter(resource_type='LSA').count()
    total_count = ResourceAgent.objects.count()
    
    print(f"  Crossroad Agents (CA):        {ca_count}")
    print(f"  Logical Segment Agents (LSA): {lsa_count}")
    print(f"  Total Resources:              {total_count}")
    
    print("\n✅ Sample resources created successfully!")
    print("\nYou can now:")
    print("  1. Run test_reservation_table.py to test the system")
    print("  2. Access Django Admin to view/manage resources")
    print("  3. Use the API endpoints to query and book slots")


if __name__ == "__main__":
    try:
        create_sample_resources()
    except Exception as e:
        print(f"\n❌ Error creating sample resources: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
