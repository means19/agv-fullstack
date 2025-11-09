#!/usr/bin/env python
"""Setup test AGVs with valid current_node for auction testing"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agv_server.settings')
django.setup()

from agv_data.models import Agv

def setup_idle_agvs():
    """Create 3 idle AGVs at different locations"""
    
    print("=" * 60)
    print("SETTING UP TEST AGVs")
    print("=" * 60)
    
    # Delete existing test AGVs
    deleted = Agv.objects.filter(agv_id__in=[1, 2, 3]).delete()
    print(f"\n✓ Deleted {deleted[0]} existing AGVs")
    
    # Create AGVs
    agvs_data = [
        {
            "agv_id": 1,
            "current_node": 2,
            "location": "CA-02"
        },
        {
            "agv_id": 2,
            "current_node": 8,
            "location": "CA-08"
        },
        {
            "agv_id": 3,
            "current_node": 6,
            "location": "CA-06"
        },
    ]
    
    print("\nCreating AGVs:")
    for data in agvs_data:
        agv = Agv.objects.create(
            agv_id=data["agv_id"],
            preferred_parking_node=1,
            motion_state=Agv.IDLE,
            current_node=data["current_node"],
            remaining_path=[],
            journey_phase=Agv.OUTBOUND  # 0 = Outbound (empty)
        )
        print(f"  ✓ AGV {agv.agv_id}: IDLE at node {agv.current_node} ({data['location']})")
    
    print("\n" + "=" * 60)
    print("✓ SETUP COMPLETE: 3 idle AGVs ready for testing")
    print("=" * 60)

if __name__ == "__main__":
    setup_idle_agvs()
