# Map Service Refactoring Guide

**Date**: December 2, 2025  
**Status**: ✅ COMPLETED

---

## Overview

The Map Service has been refactored following clean architecture principles with a focus on:
- **Separation of Concerns**: Services split by responsibility
- **OOP Design Patterns**: Manager pattern, Service layer pattern
- **Maintainability**: Clear structure, proper error handling
- **Simplicity**: Not over-engineered, pragmatic approach

---

## Architecture

### Previous Structure (Legacy)
```
map_data/
├── models.py                    # Models without managers
├── services/
│   └── map_service.py          # Single service with all logic
└── views.py                    # Function-based views
```

### New Structure (Refactored)
```
map_data/
├── models.py                    # Models with custom managers
├── exceptions.py                # Custom exception classes
├── constants.py                 # Constants (unchanged)
├── services/
│   ├── __init__.py             # Service exports
│   ├── import_service.py       # MapImportService (CSV imports)
│   ├── query_service.py        # MapQueryService (data queries)
│   └── validation_service.py   # MapValidationService (validation logic)
└── views.py                    # Class-based API views
```

---

## Design Patterns Applied

### 1. **Manager Pattern** (Django ORM)
Custom model managers encapsulate database queries.

**MapDataManager**:
```python
class MapDataManager(models.Manager):
    def get_or_create_default(self):
        return self.get_or_create(id=1)
    
    def update_node_count(self, count: int):
        map_data, _ = self.get_or_create_default()
        map_data.node_count = count
        map_data.save()
        return map_data

# Usage
MapData.objects.update_node_count(50)
```

**ConnectionManager**:
```python
class ConnectionManager(models.Manager):
    def get_connections_for_node(self, node_id: int):
        return self.filter(Q(node1=node_id) | Q(node2=node_id))
    
    def get_distance(self, node1: int, node2: int):
        try:
            connection = self.get(node1=node1, node2=node2)
            return connection.distance
        except self.model.DoesNotExist:
            return None
    
    def bulk_create_connections(self, connections: list):
        self.all().delete()
        return self.bulk_create(connections)

# Usage
Connection.objects.get_distance(1, 2)  # Returns distance or None
```

**DirectionManager**:
```python
class DirectionManager(models.Manager):
    def get_direction(self, from_node: int, to_node: int):
        # Returns direction value or None
    
    def get_directions_for_node(self, node_id: int):
        return self.filter(node1=node_id)
    
    def bulk_create_directions(self, directions: list):
        # Clear and bulk create
```

### 2. **Service Layer Pattern**
Business logic separated into focused service classes.

#### MapImportService
**Responsibility**: Import map data from CSV files

```python
class MapImportService:
    def import_connections(self, data: str) -> Dict[str, Any]:
        """Import connections with validation and transaction"""
        
    def import_directions(self, data: str) -> Dict[str, Any]:
        """Import directions with validation and transaction"""
```

**Features**:
- `@transaction.atomic` for data integrity
- CSV validation before import
- Bulk operations for performance
- Detailed import statistics

#### MapQueryService
**Responsibility**: Query and retrieve map data

```python
class MapQueryService:
    @staticmethod
    def get_all_nodes() -> List[int]:
        """Get all unique nodes"""
    
    @staticmethod
    def get_complete_map_data() -> Dict[str, Any]:
        """Get nodes, connections, directions"""
        
    @staticmethod
    def get_map_statistics() -> Dict[str, int]:
        """Get map statistics"""
        
    @staticmethod
    def delete_all_map_data() -> Dict[str, Any]:
        """Delete all map data"""
```

**Features**:
- Static methods (no state needed)
- Comprehensive error handling
- Structured return values

#### MapValidationService
**Responsibility**: Validate map data inputs

```python
class MapValidationService:
    @staticmethod
    def validate_csv_data(data: str) -> List[List[str]]:
        """Parse and validate CSV format"""
        
    @staticmethod
    def validate_direction_value(value: int) -> bool:
        """Validate direction is 1-4 or NO_CONNECTION"""
        
    @staticmethod
    def validate_distance_value(value: float) -> bool:
        """Validate distance is non-negative"""
        
    @staticmethod
    def is_valid_connection(node1: int, node2: int, value: float) -> bool:
        """Check if connection is valid (not self-loop, not NO_CONNECTION)"""
```

**Features**:
- Reusable validation logic
- Custom exceptions for specific errors
- Clear error messages

### 3. **Exception Hierarchy**
Custom exceptions for better error handling.

```python
MapDataException                    # Base exception
├── InvalidMapDataException         # Invalid format
├── MapDataNotFoundException        # Data not found
├── MapDataImportException          # Import failures
├── InvalidCSVFormatException       # CSV parsing errors
└── InvalidDirectionException       # Direction validation errors
```

**Benefits**:
- Specific exception handling
- Extra data support for context
- Consistent error responses

### 4. **Class-Based Views (DRF)**
RESTful API views with clear structure.

```python
class ImportConnectionsAPIView(APIView):
    """Import connections endpoint"""
    
    def post(self, request):
        # Handle connection import
        
class MapDataAPIView(APIView):
    """Get complete map data"""
    
    def get(self, request):
        # Return map data or error
```

**Benefits**:
- Built-in request/response handling
- Proper HTTP status codes
- DRF serialization support
- Clear endpoint responsibilities

---

## Key Improvements

### 1. **Code Organization**
- ✅ Single Responsibility Principle (each service has one job)
- ✅ Separation of Concerns (models, services, views, validation)
- ✅ Dependency Injection (services injected into views)

### 2. **Error Handling**
**Before**:
```python
return {"success": False, "message": "Error"}
```

**After**:
```python
raise MapDataImportException("Specific error message")
# Caught in view with proper HTTP status
```

### 3. **Database Operations**
**Before**:
```python
Connection.objects.all().delete()
Connection.objects.bulk_create(connections)
```

**After**:
```python
Connection.objects.bulk_create_connections(connections)
# Encapsulated in manager
```

### 4. **Validation**
**Before**:
```python
if value != MapConstants.NO_CONNECTION:
    # create object
```

**After**:
```python
if MapValidationService.is_valid_connection(node1, node2, value):
    MapValidationService.validate_distance_value(value)
    # create object
```

### 5. **API Responses**
**Before**:
```python
return JsonResponse({"error": str(e)}, status=500)
```

**After**:
```python
return Response(
    {"success": False, "error": str(e)},
    status=status.HTTP_500_INTERNAL_SERVER_ERROR
)
```

---

## API Endpoints (Updated)

### 1. POST `/api/map/import-connections/`
**Service**: `MapImportService.import_connections()`

**Request**: Raw CSV data
**Response**:
```json
{
  "success": true,
  "message": "Connection data imported successfully",
  "connection_count": 24,
  "node_count": 11
}
```

### 2. POST `/api/map/import-directions/`
**Service**: `MapImportService.import_directions()`

**Request**: Raw CSV data
**Response**:
```json
{
  "success": true,
  "message": "Direction data imported successfully",
  "direction_count": 24
}
```

### 3. GET `/api/map/get/`
**Service**: `MapQueryService.get_complete_map_data()`

**Response** (Success):
```json
{
  "success": true,
  "data": {
    "nodes": [1, 2, 3, ...],
    "connections": [...],
    "directions": [...],
    "node_count": 11,
    "connection_count": 24,
    "direction_count": 24
  }
}
```

**Response** (Partial - 206):
```json
{
  "success": false,
  "error": "Direction data is missing",
  "missing": ["directions"],
  "available": {
    "nodes": [...],
    "connections": [...]
  }
}
```

### 4. POST `/api/map/delete/`
**Service**: `MapQueryService.delete_all_map_data()`

**Response**:
```json
{
  "success": true,
  "deleted": {
    "deleted_connections": 24,
    "deleted_directions": 24,
    "deleted_map_data": 1
  }
}
```

### 5. GET `/api/map/statistics/` ⭐ NEW
**Service**: `MapQueryService.get_map_statistics()`

**Response**:
```json
{
  "success": true,
  "statistics": {
    "total_nodes": 11,
    "total_connections": 24,
    "total_directions": 24,
    "map_data_entries": 1
  }
}
```

---

## Usage Examples

### Import Map Data
```python
from map_data.services import MapImportService

import_service = MapImportService()

# Import connections
with open('connections.csv', 'r') as f:
    result = import_service.import_connections(f.read())
    print(f"Imported {result['connection_count']} connections")

# Import directions
with open('directions.csv', 'r') as f:
    result = import_service.import_directions(f.read())
    print(f"Imported {result['direction_count']} directions")
```

### Query Map Data
```python
from map_data.services import MapQueryService

query_service = MapQueryService()

# Get complete map
data = query_service.get_complete_map_data()
print(f"Map has {data['node_count']} nodes")

# Get connections for specific node
connections = query_service.get_connections_for_node(node_id=1)

# Get distance between nodes
distance = query_service.get_distance_between_nodes(1, 2)

# Get statistics
stats = query_service.get_map_statistics()
```

### Use Model Managers
```python
from map_data.models import Connection, Direction

# Get distance using manager
distance = Connection.objects.get_distance(node1=1, node2=2)

# Get all connections for node
connections = Connection.objects.get_connections_for_node(node_id=1)

# Get direction using manager
direction = Direction.objects.get_direction(from_node=1, to_node=2)
```

---

## Testing

### Unit Tests (Future Enhancement)
```python
from django.test import TestCase
from map_data.services import MapValidationService
from map_data.exceptions import InvalidCSVFormatException

class ValidationServiceTest(TestCase):
    def test_validate_csv_data(self):
        csv_data = "1,2,3\n4,5,6\n7,8,9"
        matrix = MapValidationService.validate_csv_data(csv_data)
        self.assertEqual(len(matrix), 3)
        
    def test_invalid_csv_raises_exception(self):
        with self.assertRaises(InvalidCSVFormatException):
            MapValidationService.validate_csv_data("")
```

### Integration Tests
```bash
# Start server
docker compose up server

# Test import
curl -X POST http://localhost:8000/api/map/import-connections/ \
  --data-binary @connections.csv

# Test query
curl http://localhost:8000/api/map/get/

# Test statistics
curl http://localhost:8000/api/map/statistics/
```

---

## Migration Guide

### For Developers Using Old Code

**Old**:
```python
from map_data.services.map_service import MapService

result = MapService.import_connections(data)
```

**New**:
```python
from map_data.services import MapImportService

import_service = MapImportService()
result = import_service.import_connections(data)
```

**Old**:
```python
result = MapService.get_map_data()
data = result["data"]
```

**New**:
```python
from map_data.services import MapQueryService

query_service = MapQueryService()
data = query_service.get_complete_map_data()
```

### Breaking Changes
- ❌ `MapService` class removed
- ❌ Function-based views removed
- ✅ New service classes with same functionality
- ✅ Class-based views with DRF

---

## Performance Considerations

### Database Optimization
- **Bulk Operations**: Use `bulk_create_connections()` and `bulk_create_directions()`
- **Indexes**: Node1 and node2 fields are indexed
- **Transactions**: Import operations wrapped in `@transaction.atomic`

### Query Optimization
- **Manager Methods**: Encapsulate complex queries
- **Select Related**: Can be added for FK optimization (future)
- **Caching**: Can be added for frequently accessed data (future)

---

## Future Enhancements

### Potential Improvements
1. **Caching Layer**: Redis cache for map data
2. **Async Views**: Use DRF async views for better performance
3. **Serializers**: DRF serializers for structured responses
4. **Pagination**: For large map datasets
5. **Versioning**: API versioning support
6. **GraphQL**: Alternative query interface
7. **WebSockets**: Real-time map updates
8. **Tests**: Comprehensive unit and integration tests

### Integration Opportunities
1. **ResourceAgent**: Unify with new map system (hybrid approach)
2. **NetworkX**: Add graph algorithms
3. **Frontend**: React components for map visualization
4. **Monitoring**: Prometheus metrics for map operations

---

## Conclusion

✅ **Refactoring Complete**

**Improvements**:
- Clear separation of concerns
- Better error handling with custom exceptions
- Reusable validation logic
- Maintainable service layer
- DRF-standard API views
- Custom model managers for clean queries

**Benefits**:
- Easier to test
- Easier to extend
- More maintainable
- Better documentation
- Industry-standard patterns

**Next Steps**:
- Add comprehensive tests
- Consider caching layer
- Integrate with ResourceAgent system
- Add API documentation (Swagger/OpenAPI)

---

**Refactored By**: AI Assistant  
**Review Status**: Ready for code review  
**Documentation**: Up to date
