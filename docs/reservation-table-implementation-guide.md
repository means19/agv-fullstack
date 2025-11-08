# Hướng dẫn Sử dụng Reservation Table System

## Tổng quan
Đã implement thành công Reservation Table cho hệ thống D-MAS (Delegate Multi-Agent System). Hệ thống cho phép các AGV "Ants" (Exploring và Intention) đặt chỗ tài nguyên (CA và LSA) hiệu quả, xử lý xung đột và concurrency.

## Các thành phần đã implement

### 1. Models (agv_data/models.py)
- **ResourceAgent**: Đại diện cho tài nguyên có thể đặt chỗ (CA hoặc LSA)
- **Booking**: Đại diện cho một lần đặt chỗ với start_time và end_time

### 2. Service Layer (agv_data/services.py)
- **find_earliest_available_slot()**: Tìm khe trống sớm nhất (Exploring Ant)
- **create_booking()**: Tạo booking (Intention Ant)
- **get_bookings_for_agv()**: Lấy danh sách booking của AGV
- **get_bookings_for_resource()**: Lấy danh sách booking của resource
- **cancel_booking()**: Hủy booking
- **cancel_agv_bookings()**: Hủy tất cả booking của AGV

### 3. API Endpoints (agv_data/views.py & urls.py)

#### Query Slot (Exploring Ant)
```
POST /api/agvs/reservation/resource/<resource_id>/query_slot/
Body:
{
    "request_start_time": "2025-11-07T15:30:00Z",
    "duration_seconds": 15
}
```

#### Book Slot (Intention Ant)
```
POST /api/agvs/reservation/resource/<resource_id>/book_slot/
Body:
{
    "agv_id": 2,
    "request_start_time": "2025-11-07T15:30:00Z",
    "duration_seconds": 15
}
```

#### List Bookings
```
GET /api/agvs/reservation/bookings/?agv_id=<agv_id>
GET /api/agvs/reservation/bookings/?resource_id=<resource_id>
```

#### Cancel Booking
```
DELETE /api/agvs/reservation/bookings/<booking_id>/
```

#### List Resources
```
GET /api/agvs/reservation/resources/
```

### 4. Management Command (agv_data/management/commands/cleanup_bookings.py)
Lệnh để xóa các booking cũ:
```bash
python manage.py cleanup_bookings --days 1
python manage.py cleanup_bookings --days 7 --dry-run
```

## Cách chạy

### Bước 1: Chạy Migrations

#### Sử dụng Docker (khuyến nghị):
```bash
# Khởi động Docker containers
docker-compose up -d

# Chạy migrations
docker-compose exec server python manage.py makemigrations
docker-compose exec server python manage.py migrate
```

#### Sử dụng Local Development:
```bash
cd agv_server
python manage.py makemigrations
python manage.py migrate
```

### Bước 2: Tạo Sample Resources

Truy cập Django Admin (http://localhost:8000/admin) hoặc sử dụng Django shell:

```python
# Sử dụng Docker
docker-compose exec server python manage.py shell

# Hoặc local
python manage.py shell
```

Trong shell:
```python
from agv_data.models import ResourceAgent

# Tạo Crossroad Agents
ca1 = ResourceAgent.objects.create(name="CA_01", resource_type="CA")
ca2 = ResourceAgent.objects.create(name="CA_02", resource_type="CA")
ca3 = ResourceAgent.objects.create(name="CA_03", resource_type="CA")

# Tạo Logical Segment Agents
lsa1 = ResourceAgent.objects.create(name="LSA_01_02", resource_type="LSA")
lsa2 = ResourceAgent.objects.create(name="LSA_02_03", resource_type="LSA")
lsa3 = ResourceAgent.objects.create(name="LSA_03_04", resource_type="LSA")

print("Sample resources created successfully!")
```

### Bước 3: Test API Endpoints

#### Test 1: Query Slot (Exploring Ant)
```bash
curl -X POST http://localhost:8000/api/agvs/reservation/resource/1/query_slot/ \
  -H "Content-Type: application/json" \
  -d '{
    "request_start_time": "2025-11-07T15:30:00Z",
    "duration_seconds": 15
  }'
```

#### Test 2: Book Slot (Intention Ant)
```bash
curl -X POST http://localhost:8000/api/agvs/reservation/resource/1/book_slot/ \
  -H "Content-Type: application/json" \
  -d '{
    "agv_id": 1,
    "request_start_time": "2025-11-07T15:30:00Z",
    "duration_seconds": 15
  }'
```

#### Test 3: List Bookings for AGV
```bash
curl http://localhost:8000/api/agvs/reservation/bookings/?agv_id=1
```

#### Test 4: List All Resources
```bash
curl http://localhost:8000/api/agvs/reservation/resources/
```

#### Test 5: Cancel Booking
```bash
curl -X DELETE http://localhost:8000/api/agvs/reservation/bookings/1/
```

### Bước 4: Schedule Cleanup (Tùy chọn)

Để tự động cleanup bookings cũ, thêm vào crontab (Linux/Mac) hoặc Task Scheduler (Windows):

```bash
# Chạy hàng ngày lúc 3:00 AM
0 3 * * * docker-compose exec -T server python manage.py cleanup_bookings --days 1
```

## Python Test Script

Tạo file `test_reservation_table.py` trong thư mục gốc project:

```python
import requests
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:8000/api/agvs/reservation"

def test_reservation_system():
    print("=== Testing Reservation Table System ===\n")
    
    # Test 1: List all resources
    print("1. Listing all resources...")
    response = requests.get(f"{BASE_URL}/resources/")
    print(f"Status: {response.status_code}")
    resources = response.json()
    print(f"Found {len(resources)} resources")
    print(json.dumps(resources, indent=2))
    
    if not resources:
        print("\nNo resources found. Please create some first!")
        return
    
    resource_id = resources[0]['id']
    print(f"\nUsing resource_id: {resource_id} for testing\n")
    
    # Test 2: Query slot
    print("2. Querying earliest available slot...")
    now = datetime.utcnow()
    query_data = {
        "request_start_time": now.isoformat() + "Z",
        "duration_seconds": 30
    }
    response = requests.post(
        f"{BASE_URL}/resource/{resource_id}/query_slot/",
        json=query_data
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    # Test 3: Book slot
    print("\n3. Booking a slot...")
    book_data = {
        "agv_id": 1,
        "request_start_time": now.isoformat() + "Z",
        "duration_seconds": 30
    }
    response = requests.post(
        f"{BASE_URL}/resource/{resource_id}/book_slot/",
        json=book_data
    )
    print(f"Status: {response.status_code}")
    booking = response.json()
    print(json.dumps(booking, indent=2))
    
    if response.status_code == 201:
        booking_id = booking['id']
        
        # Test 4: List bookings for AGV
        print("\n4. Listing bookings for AGV 1...")
        response = requests.get(f"{BASE_URL}/bookings/?agv_id=1")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        # Test 5: Book another slot (should not conflict)
        print("\n5. Booking another slot (2 minutes later)...")
        later_time = now + timedelta(minutes=2)
        book_data2 = {
            "agv_id": 2,
            "request_start_time": later_time.isoformat() + "Z",
            "duration_seconds": 30
        }
        response = requests.post(
            f"{BASE_URL}/resource/{resource_id}/book_slot/",
            json=book_data2
        )
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        # Test 6: Cancel booking
        print(f"\n6. Cancelling booking {booking_id}...")
        response = requests.delete(f"{BASE_URL}/bookings/{booking_id}/")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    try:
        test_reservation_system()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")
```

## Kiến trúc và Đặc điểm Kỹ thuật

### Xử lý Concurrency
- Sử dụng `transaction.atomic` với Django ORM
- `select_for_update()` để lock records khi đọc
- Isolation level được xử lý bởi PostgreSQL (READ COMMITTED mặc định)

### Database Indexes
- Index trên `(resource, start_time)`
- Index trên `(resource, end_time)`
- Index trên `agv_id`

### Performance Considerations
- Query tối ưu với filter và ordering
- Sử dụng `select_related()` khi cần
- Cleanup định kỳ để giữ database nhỏ gọn

## Tích hợp với Sequential Single Item + D-MAS

### Luồng hoạt động:

1. **Exploring Ant Phase**:
   - AGV gửi request đến `query_slot` để tìm khe trống
   - Nhận về thời gian sớm nhất có thể đặt chỗ
   - Tính toán delay nếu cần chờ

2. **Intention Ant Phase**:
   - Sau khi quyết định đi theo đường nào, AGV gửi `book_slot`
   - System tạo booking atomically
   - Nếu có conflict, trả về 409 và AGV retry

3. **Execution Phase**:
   - AGV di chuyển theo lịch đã đặt
   - Khi hoàn thành, có thể cancel booking hoặc để cleanup tự động xóa

### Mapping với thuật toán:

- **ResourceAgent (CA)** = Crossroad Agent (điểm giao cắt)
- **ResourceAgent (LSA)** = Logical Segment Agent (đoạn đường giữa 2 node)
- **Booking.start_time** = Thời điểm AGV bắt đầu chiếm dụng resource
- **Booking.end_time** = Thời điểm AGV giải phóng resource

## Troubleshooting

### Lỗi common:

1. **ModuleNotFoundError: No module named 'dotenv'**
   - Giải pháp: Sử dụng Docker thay vì local development

2. **Migration errors**
   - Giải pháp: Đảm bảo database đang chạy và migrations được chạy theo thứ tự

3. **Booking conflicts**
   - Đây là behavior bình thường, AGV cần retry với query_slot để tìm slot mới

## Bước tiếp theo

1. ✅ Reservation Table đã được implement
2. 📝 Tiếp theo: Implement Sequential Single Item algorithm
3. 📝 Tích hợp Exploring Ant và Intention Ant
4. 📝 Implement D-MAS decision making logic
5. 📝 Test toàn bộ hệ thống với multiple AGVs

## Tài liệu tham khảo

- `docs/reservation_table.md` - Đặc tả kỹ thuật gốc
- `agv_data/models.py` - Models implementation
- `agv_data/services.py` - Business logic
- `agv_data/views.py` - API endpoints
- `agv_data/admin.py` - Django admin configuration
