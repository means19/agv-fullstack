"""
Repository for ResourceAgent operations.
"""

from typing import Optional
from django.db import transaction
from agv_data.models import ResourceAgent
from ..domain.exceptions import ResourceNotFoundError


class ResourceRepository:
    """
    Repository for ResourceAgent persistence operations.
    Handles database access for resource entities.
    """
    
    @transaction.atomic
    def find_by_id(self, resource_id: int, lock: bool = False) -> ResourceAgent:
        """
        Find a resource by its ID.
        
        Args:
            resource_id: The ID of the resource
            lock: If True, acquire a database lock (for concurrent access)
            
        Returns:
            ResourceAgent instance
            
        Raises:
            ResourceNotFoundError: If resource does not exist
        """
        try:
            queryset = ResourceAgent.objects
            if lock:
                queryset = queryset.select_for_update()
            return queryset.get(id=resource_id)
        except ResourceAgent.DoesNotExist:
            raise ResourceNotFoundError(f"Resource with ID={resource_id} does not exist.")
    
    def exists(self, resource_id: int) -> bool:
        """Check if a resource exists."""
        return ResourceAgent.objects.filter(id=resource_id).exists()
