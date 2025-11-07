# Đặc tả Kỹ thuật: Mô-đun Bảng Đặt Chỗ (Reservation Table)

## 1. Giới thiệu
### 1.1 Mục tiêu
Tài liệu này hướng dẫn implement Mô-đun Bảng Đặt Chỗ (Reservation Table) cho hệ thống D-MAS (Delegate Multi‑Agent System) của AGV.  
Mục tiêu: tạo một dịch vụ phía server (Django) cho phép các AGV "Ants" (Exploring và Intention) truy vấn khe thời gian (time slots) và đặt chỗ (book) tài nguyên (CA và LSA) hiệu quả, xử lý xung đột và concurrency.

### 1.2 Công nghệ
- Backend: Django 4.x+
- Database: PostgreSQL (hỗ trợ `select_for_update` hiệu quả)
- API: Django Rest Framework (DRF)
- Thiết kế: Sử dụng Django ORM + index database để mô phỏng “Reservation Table” (thay cho BST trong bộ nhớ)

---

## 2. Cấu trúc Dữ liệu (Models)
Vị trí: `[app_name]/models.py`

### 2.1 Model ResourceAgent
Đại diện tài nguyên có thể đặt chỗ (CA hoặc LSA).

```python
# [app_name]/models.py

from django.db import models

class ResourceAgent(models.Model):
    """
    Đại diện cho một tài nguyên có thể được đặt chỗ:
    Crossroad Agent (CA) hoặc Logical Segment Agent (LSA).
    """
    class ResourceType(models.TextChoices):
        CROSSROAD = 'CA', 'Crossroad Agent'
        SEGMENT = 'LSA', 'Logical Segment Agent'

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Tên định danh duy nhất, vd: 'CA_01' hoặc 'LSA_01_02'"
    )
    resource_type = models.CharField(
        max_length=3,
        choices=ResourceType.choices,
        help_text="Loại tài nguyên (CA hoặc LSA)"
    )

    def __str__(self):
        return self.name
```

### 2.2 Model Booking
Đại diện cho một lần đặt chỗ (một "node" trong bảng đặt chỗ). Mỗi `ResourceAgent` có nhiều `Booking`.

```python
# [app_name]/models.py (tiếp)

from django.utils import timezone

class Booking(models.Model):
    """
    Đại diện cho một lần đặt chỗ.
    """
    resource = models.ForeignKey(
        ResourceAgent,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="Tài nguyên (CA/LSA) được đặt chỗ"
    )
    agv_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="AGV thực hiện đặt chỗ"
    )
    start_time = models.DateTimeField(help_text="Thời điểm bắt đầu chiếm dụng")
    end_time = models.DateTimeField(help_text="Thời điểm giải phóng tài nguyên")

    class Meta:
        # Tạo các index để tối ưu filter theo tài nguyên và thời gian
        indexes = [
            models.Index(fields=['resource', 'start_time']),
            models.Index(fields=['resource', 'end_time']),
        ]

    def __str__(self):
        return f"{self.agv_id} @ {self.resource.name} [{self.start_time} - {self.end_time}]"
```

Hành động: sau khi định nghĩa models, chạy:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 3. Logic Nghiệp vụ (Services)
Vị trí: `[app_name]/services.py`  
Không đặt logic trong `views.py`; đặt vào `services.py`.

### 3.1 Định nghĩa lỗi nghiệp vụ

```python
# [app_name]/services.py

from django.db import transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone
from .models import ResourceAgent, Booking
from datetime import timedelta

class BookingConflictError(Exception):
    """Ném ra khi có xung đột đặt chỗ không thể giải quyết."""
    pass

class ResourceNotFoundError(Exception):
    """Ném ra khi ResourceAgent ID không tồn tại."""
    pass
```

### 3.2 Hàm find_earliest_available_slot (Exploring Ant)
Tìm khe trống sớm nhất, chỉ đọc (không tạo record). Sử dụng isolation/locking để đảm bảo tính nhất quán.

```python
@transaction.atomic(isolation=transaction.ISOLATION_SERIALIZABLE)
def find_earliest_available_slot(resource_id: int, request_start_time: timezone.datetime, duration: timedelta):
    """
    Tìm khe trống sớm nhất cho resource_id, kể từ request_start_time, đủ length duration.
    """
    if duration <= timedelta(seconds=0):
        raise ValueError("Duration phải là số dương.")

    try:
        ResourceAgent.objects.get(id=resource_id)
    except ResourceAgent.DoesNotExist:
        raise ResourceNotFoundError(f"Tài nguyên với ID={resource_id} không tồn tại.")

    current_check_time = request_start_time

    while True:
        request_end_time = current_check_time + duration

        conflicting_booking = Booking.objects.filter(
            resource_id=resource_id,
            start_time__lt=request_end_time,
            end_time__gt=current_check_time
        ).order_by('end_time').first()

        if conflicting_booking:
            current_check_time = conflicting_booking.end_time
        else:
            return current_check_time
```

### 3.3 Hàm create_booking (Intention Ant)
Tạo booking trong một giao dịch nguyên tử; nếu có race condition, transaction sẽ fail và caller cần retry.

```python
@transaction.atomic(isolation=transaction.ISOLATION_SERIALIZABLE)
def create_booking(resource_id: int, agv_id: str, requested_start_time: timezone.datetime, duration: timedelta):
    """
    Tạo booking cho agv_id; trả về instance Booking nếu thành công.
    """
    try:
        actual_start_time = find_earliest_available_slot(
            resource_id=resource_id,
            request_start_time=requested_start_time,
            duration=duration
        )
    except ResourceNotFoundError:
        raise

    actual_end_time = actual_start_time + duration

    try:
        new_booking = Booking.objects.create(
            resource_id=resource_id,
            agv_id=agv_id,
            start_time=actual_start_time,
            end_time=actual_end_time
        )
        return new_booking
    except DatabaseError as e:
        raise BookingConflictError(f"Không thể đặt chỗ do xung đột đồng thời: {str(e)}")
```

---

## 4. API Endpoints
Vị trí: `[app_name]/views.py`, `[app_name]/urls.py`  
Sử dụng DRF để triển khai endpoints cho Exploring và Intention Ant.

### 4.1 views.py

```python
# [app_name]/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import services
from .serializers import BookingSerializer
from datetime import timedelta
from django.utils.dateparse import parse_datetime

class QuerySlotView(APIView):
    """
    POST /api/resource/<int:resource_id>/query_slot/
    Body:
    {
        "request_start_time": "2025-11-07T15:30:00Z",
        "duration_seconds": 15
    }
    """
    def post(self, request, resource_id, format=None):
        try:
            start_time_str = request.data.get('request_start_time')
            duration_sec = int(request.data.get('duration_seconds'))
            start_time = parse_datetime(start_time_str)
            if not start_time:
                raise ValueError("Định dạng 'request_start_time' không hợp lệ.")
            duration = timedelta(seconds=duration_sec)

            earliest_slot_start = services.find_earliest_available_slot(
                resource_id=resource_id,
                request_start_time=start_time,
                duration=duration
            )

            delay_seconds = (earliest_slot_start - start_time).total_seconds()

            return Response({
                "resource_id": resource_id,
                "earliest_available_start": earliest_slot_start,
                "requested_duration_seconds": duration_sec,
                "calculated_delay_seconds": delay_seconds
            }, status=status.HTTP_200_OK)

        except (ValueError, TypeError) as e:
            return Response({"error": f"Dữ liệu đầu vào không hợp lệ: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except services.ResourceNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Lỗi máy chủ: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BookSlotView(APIView):
    """
    POST /api/resource/<int:resource_id>/book_slot/
    Body:
    {
        "agv_id": "AGV_002",
        "request_start_time": "2025-11-07T15:30:00Z",
        "duration_seconds": 15
    }
    """
    def post(self, request, resource_id, format=None):
        try:
            agv_id = request.data.get('agv_id')
            start_time_str = request.data.get('request_start_time')
            duration_sec = int(request.data.get('duration_seconds'))

            if not agv_id or not start_time_str or not duration_sec:
                raise ValueError("Thiếu các trường 'agv_id', 'request_start_time', hoặc 'duration_seconds'.")

            start_time = parse_datetime(start_time_str)
            if not start_time:
                raise ValueError("Định dạng 'request_start_time' không hợp lệ.")

            duration = timedelta(seconds=duration_sec)

            new_booking = services.create_booking(
                resource_id=resource_id,
                agv_id=agv_id,
                requested_start_time=start_time,
                duration=duration
            )

            serializer = BookingSerializer(new_booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (ValueError, TypeError) as e:
            return Response({"error": f"Dữ liệu đầu vào không hợp lệ: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except services.ResourceNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except services.BookingConflictError as e:
            return Response({"error": f"Xung đột đặt chỗ (thử lại): {str(e)}"}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({"error": f"Lỗi máy chủ: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

### 4.2 serializers.py

```python
# [app_name]/serializers.py

from rest_framework import serializers
from .models import Booking

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'resource', 'agv_id', 'start_time', 'end_time']
```

### 4.3 urls.py

```python
# [app_name]/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('api/resource/<int:resource_id>/query_slot/', views.QuerySlotView.as_view(), name='query-slot'),
    path('api/resource/<int:resource_id>/book_slot/', views.BookSlotView.as_view(), name='book-slot'),
]
```

---

## 5. Nhiệm vụ Dọn dẹp (cleanup)
Booking sẽ tăng nhanh; cần cron hoặc Celery để xóa booking cũ.

### 5.1 Management Command

```python
# [app_name]/management/commands/cleanup_bookings.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from ...models import Booking
from datetime import timedelta

class Command(BaseCommand):
    help = 'Xóa các bản ghi booking cũ đã hoàn thành.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=1, help='Số ngày giữ lại booking cũ.')

    def handle(self, *args, **options):
        days_to_keep = options['days']
        cutoff_time = timezone.now() - timedelta(days=days_to_keep)

        self.stdout.write(f"Bắt đầu dọn dẹp các booking cũ hơn {cutoff_time}...")

        deleted_count, _ = Booking.objects.filter(end_time__lt=cutoff_time).delete()

        self.stdout.write(self.style.SUCCESS(f"Đã xóa thành công {deleted_count} booking cũ."))
```

### 5.2 Lên lịch (cron)
Chạy hàng ngày (ví dụ 3:00 AM):

```bash
# crontab -e
0 3 * * * /path/to/your/project/manage.py cleanup_bookings --days 1
```

---

KẾT THÚC TÀI LIỆU
