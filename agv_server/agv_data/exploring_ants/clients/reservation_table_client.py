"""
Reservation Table API Client for Exploring Ant

This module provides a client for querying the Reservation Table API.
The API returns the earliest available time slot for a given resource.
"""

import requests
from datetime import datetime
from typing import Optional, Dict
from ..config import APIConfig, DEFAULT_CONFIG


class ReservationTableAPIError(Exception):
    """Exception raised when Reservation Table API call fails."""
    pass


class ReservationTableClient:
    """
    Client for interacting with the Reservation Table API.
    
    The Reservation Table manages resource reservations (CA and LSA nodes)
    and provides slot availability information for AGV planning.
    
    Attributes:
        config: API configuration (base URL, timeout)
        
    Example:
        >>> client = ReservationTableClient()
        >>> response = client.query_slot(
        ...     resource_id=5,
        ...     desired_start=datetime.now(timezone.utc),
        ...     duration_sec=30.0
        ... )
        >>> if response:
        ...     print(f"Available at: {response['earliest_available_start']}")
    """
    
    def __init__(self, config: APIConfig = None):
        """
        Initialize the Reservation Table client.
        
        Args:
            config: API configuration. If None, uses DEFAULT_CONFIG.api
        """
        self.config = config or DEFAULT_CONFIG.api
    
    def query_slot(
        self,
        resource_id: int,
        desired_start: datetime,
        duration_sec: float
    ) -> Optional[Dict]:
        """
        Query the Reservation Table API for the earliest available slot.
        
        Args:
            resource_id: ID of the resource (CA or LSA)
            desired_start: Desired start time for the reservation
            duration_sec: Duration of the reservation in seconds
            
        Returns:
            Dict with 'earliest_available_start' key or None if API fails
            
        Raises:
            ReservationTableAPIError: If API call fails or returns invalid response
            
        Example:
            >>> client = ReservationTableClient()
            >>> from datetime import datetime, timezone
            >>> response = client.query_slot(
            ...     resource_id=5,
            ...     desired_start=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            ...     duration_sec=30.0
            ... )
            >>> print(response['earliest_available_start'])
            2025-01-15T10:00:00+00:00
        """
        url = f"{self.config.reservation_api_url}/resource/{resource_id}/query_slot/"
        
        payload = {
            "request_start_time": desired_start.isoformat(),
            "duration_seconds": int(duration_sec)
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.config.request_timeout_sec
            )
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout as e:
            error_msg = (
                f"Reservation API timeout for resource {resource_id}\n"
                f"  URL: {url}\n"
                f"  Timeout: {self.config.request_timeout_sec}s"
            )
            raise ReservationTableAPIError(error_msg) from e
            
        except requests.HTTPError as e:
            error_msg = (
                f"Reservation API HTTP error for resource {resource_id}\n"
                f"  URL: {url}\n"
                f"  Status: {e.response.status_code if e.response else 'N/A'}\n"
                f"  Response: {e.response.text if e.response else 'N/A'}"
            )
            raise ReservationTableAPIError(error_msg) from e
            
        except requests.RequestException as e:
            error_msg = (
                f"Reservation API request failed for resource {resource_id}\n"
                f"  URL: {url}\n"
                f"  Error: {str(e)}"
            )
            raise ReservationTableAPIError(error_msg) from e
    
    def query_slot_safe(
        self,
        resource_id: int,
        desired_start: datetime,
        duration_sec: float,
        verbose: bool = False
    ) -> Optional[Dict]:
        """
        Query slot with error handling (returns None instead of raising).
        
        This is a safe version that catches all exceptions and returns None,
        suitable for use in exploration where we want to continue on failure.
        
        Args:
            resource_id: ID of the resource (CA or LSA)
            desired_start: Desired start time for the reservation
            duration_sec: Duration of the reservation in seconds
            verbose: If True, print error messages to console
            
        Returns:
            Dict with 'earliest_available_start' or None if API fails
            
        Example:
            >>> client = ReservationTableClient()
            >>> response = client.query_slot_safe(
            ...     resource_id=5,
            ...     desired_start=datetime.now(timezone.utc),
            ...     duration_sec=30.0,
            ...     verbose=True
            ... )
            >>> if response is None:
            ...     print("API call failed, route infeasible")
        """
        try:
            return self.query_slot(resource_id, desired_start, duration_sec)
        except ReservationTableAPIError as e:
            if verbose:
                print(f"[ERROR] {e}")
            return None
        except Exception as e:
            if verbose:
                print(f"[ERROR] Unexpected error querying slot: {e}")
            return None
    
    def validate_response(self, response: Optional[Dict]) -> bool:
        """
        Validate that API response contains required fields.
        
        Args:
            response: API response dictionary
            
        Returns:
            bool: True if response is valid, False otherwise
            
        Example:
            >>> client = ReservationTableClient()
            >>> response = {'earliest_available_start': '2025-01-15T10:00:00+00:00'}
            >>> client.validate_response(response)
            True
        """
        if response is None:
            return False
        if not isinstance(response, dict):
            return False
        if 'earliest_available_start' not in response:
            return False
        return True
    
    def parse_earliest_start(self, response: Dict) -> Optional[datetime]:
        """
        Parse earliest_available_start from API response.
        
        Args:
            response: API response dictionary
            
        Returns:
            datetime: Parsed datetime or None if parsing fails
            
        Example:
            >>> client = ReservationTableClient()
            >>> response = {'earliest_available_start': '2025-01-15T10:00:00+00:00'}
            >>> dt = client.parse_earliest_start(response)
            >>> print(dt)
            2025-01-15 10:00:00+00:00
        """
        if not self.validate_response(response):
            return None
        
        try:
            return datetime.fromisoformat(response['earliest_available_start'])
        except (ValueError, TypeError):
            return None
