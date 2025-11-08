# Reservation Table Quick Start Guide

## 🎯 Mục tiêu
Reservation Table đã được implement cho hệ thống D-MAS (Delegate Multi-Agent System), cho phép AGVs đặt chỗ tài nguyên (CA và LSA) một cách hiệu quả.

## 🚀 Quick Start

### 1. Chạy Migrations

```bash
# Khởi động Docker containers
docker-compose up -d

# Chạy migrations
docker-compose exec server python manage.py makemigrations
docker-compose exec server python manage.py migrate
```

### 2. Tạo Sample Resources

```bash
# Chạy script tạo sample data
docker-compose exec server python create_sample_resources.py
```

Hoặc sử dụng Django shell:
```bash
docker-compose exec server python manage.py shell
```

```python
from agv_data.models import ResourceAgent

# Tạo Crossroad Agents
ResourceAgent.objects.create(name="CA_01", resource_type="CA")
ResourceAgent.objects.create(name="CA_02", resource_type="CA")

# Tạo Logical Segment Agents  
ResourceAgent.objects.create(name="LSA_01_02", resource_type="LSA")
ResourceAgent.objects.create(name="LSA_02_03", resource_type="LSA")
```

### 3. Test Hệ thống

```bash
# Chạy functional test
python tests/test_reservation_table.py

# Chạy concurrent test (QUAN TRỌNG NHẤT!)
python tests/test_concurrent_booking.py

# Verify không có overlaps
python tests/check_overlaps.py
```

Xem chi tiết trong `tests/README.md`

Hoặc test thủ công với curl:

```bash
# Query slot (Exploring Ant)
curl -X POST http://localhost:8000/api/agvs/reservation/resource/1/query_slot/ \
  -H "Content-Type: application/json" \
  -d '{"request_start_time":"2025-11-07T15:30:00Z","duration_seconds":30}'

# Book slot (Intention Ant)
curl -X POST http://localhost:8000/api/agvs/reservation/resource/1/book_slot/ \
  -H "Content-Type: application/json" \
  -d '{"agv_id":1,"request_start_time":"2025-11-07T15:30:00Z","duration_seconds":30}'
```

## 📋 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agvs/reservation/resources/` | GET | List all resources |
| `/api/agvs/reservation/resource/<id>/query_slot/` | POST | Query earliest available slot |
| `/api/agvs/reservation/resource/<id>/book_slot/` | POST | Book a slot |
| `/api/agvs/reservation/bookings/?agv_id=<id>` | GET | List AGV bookings |
| `/api/agvs/reservation/bookings/?resource_id=<id>` | GET | List resource bookings |
| `/api/agvs/reservation/bookings/<id>/` | DELETE | Cancel booking |

## 🧹 Cleanup Old Bookings

```bash
# Dry run (xem trước)
docker-compose exec server python manage.py cleanup_bookings --days 1 --dry-run

# Thực thi xóa
docker-compose exec server python manage.py cleanup_bookings --days 1
```

## 📚 Tài liệu đầy đủ

Xem `docs/reservation-table-implementation-guide.md` để biết chi tiết.

## ✅ Checklist Implementation

- [x] Models (ResourceAgent, Booking)
- [x] Service Layer (find_earliest_available_slot, create_booking)
- [x] API Endpoints (Query, Book, List, Cancel)
- [x] Serializers (BookingSerializer, ResourceAgentSerializer)
- [x] Admin Interface
- [x] Management Command (cleanup_bookings)
- [x] Test Scripts
- [x] Documentation

## 🔜 Next Steps

1. Implement Sequential Single Item algorithm
2. Integrate Exploring Ant logic
3. Integrate Intention Ant logic
4. Implement full D-MAS decision making
5. Test with multiple AGVs
