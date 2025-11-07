import requests
import json
from datetime import datetime

resp = requests.get('http://localhost:8000/api/agvs/reservation/bookings/?resource_id=2')
bookings = resp.json()

print(f'\nTotal bookings for Resource 2: {len(bookings)}\n')
print("="*80)

for i, b in enumerate(bookings[-10:], 1):
    start = datetime.fromisoformat(b['start_time'])
    end = datetime.fromisoformat(b['end_time'])
    print(f"{i}. Booking {b['id']:3d}: AGV {b['agv_id']} | {start.strftime('%H:%M:%S.%f')[:-3]} → {end.strftime('%H:%M:%S.%f')[:-3]}")

# Check for overlaps
print("\n" + "="*80)
print("Checking for overlaps...")
overlaps = []
for i in range(len(bookings)):
    for j in range(i+1, len(bookings)):
        b1 = bookings[i]
        b2 = bookings[j]
        start1 = datetime.fromisoformat(b1['start_time'])
        end1 = datetime.fromisoformat(b1['end_time'])
        start2 = datetime.fromisoformat(b2['start_time'])
        end2 = datetime.fromisoformat(b2['end_time'])
        
        # Check overlap: start1 < end2 AND start2 < end1
        if start1 < end2 and start2 < end1:
            overlaps.append((b1['id'], b2['id']))

if overlaps:
    print(f"❌ Found {len(overlaps)} overlapping booking pairs:")
    for b1_id, b2_id in overlaps[:5]:
        print(f"   - Booking {b1_id} overlaps with Booking {b2_id}")
else:
    print("✅ NO OVERLAPS FOUND - All bookings are properly serialized!")
