"""
Service layer for Reservation Table operations.
Implements the core logic for D-MAS (Delegate Multi-Agent System) resource booking.
"""

from django.db import transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone
from .models import ResourceAgent, Booking
from datetime import timedelta


class BookingConflictError(Exception):
    """Raised when a booking conflict cannot be resolved."""
    pass


class ResourceNotFoundError(Exception):
    """Raised when a ResourceAgent ID does not exist."""
    pass


@transaction.atomic
def find_earliest_available_slot(
    resource_id: int,
    request_start_time: timezone.datetime,
    duration: timedelta
):
    """
    Find the earliest available time slot for a resource (Exploring Ant operation).
    
    This function searches for the earliest time slot that can accommodate the requested
    duration, starting from request_start_time. It uses database-level locking to ensure
    consistency in concurrent environments.
    
    Args:
        resource_id: ID of the ResourceAgent (CA or LSA)
        request_start_time: Earliest acceptable start time for the booking
        duration: Required duration of the booking
        
    Returns:
        datetime: The earliest available start time for the booking
        
    Raises:
        ValueError: If duration is not positive
        ResourceNotFoundError: If resource_id does not exist
    """
    if duration <= timedelta(seconds=0):
        raise ValueError("Duration must be positive.")
    
    # Verify resource exists
    try:
        resource = ResourceAgent.objects.select_for_update().get(id=resource_id)
    except ResourceAgent.DoesNotExist:
        raise ResourceNotFoundError(f"Resource with ID={resource_id} does not exist.")
    
    current_check_time = request_start_time
    
    # Iteratively find the earliest available slot
    while True:
        request_end_time = current_check_time + duration
        
        # Find any conflicting booking
        conflicting_booking = Booking.objects.select_for_update().filter(
            resource_id=resource_id,
            start_time__lt=request_end_time,
            end_time__gt=current_check_time
        ).order_by('end_time').first()
        
        if conflicting_booking:
            # Move to the end of the conflicting booking and try again
            current_check_time = conflicting_booking.end_time
        else:
            # No conflict found, this slot is available
            return current_check_time


@transaction.atomic
def create_booking(
    resource_id: int,
    agv_id: int,
    exact_start_time: timezone.datetime,
    duration: timedelta
):
    """
    Create a booking for an AGV (Intention Ant operation) - STRICT MODE.
    
    This function ONLY books the EXACT time slot requested. It does NOT automatically
    find alternative slots. This ensures auction integrity in SSI-DMAS:
    - AGV bids based on a specific slot from Exploring Ant
    - Intention Ant must get that EXACT slot or fail with 409
    - If it fails, AGV returns to idle and can bid on a new auction
    
    This is CRITICAL: Auto-serialization would break auction integrity because
    AGV would win auction for slot A but receive slot B with different cost.
    
    Args:
        resource_id: ID of the ResourceAgent (CA or LSA)
        agv_id: ID of the AGV making the booking
        exact_start_time: The EXACT start time that must be available (from EA)
        duration: Required duration of the booking
        
    Returns:
        Booking: The created booking instance
        
    Raises:
        ResourceNotFoundError: If resource_id does not exist
        BookingConflictError: If the EXACT slot is not available (409)
        ValueError: If duration is not positive
    """
    # Verify resource exists and LOCK it for the duration of this transaction
    # This prevents other transactions from even checking this resource
    try:
        resource = ResourceAgent.objects.select_for_update().get(id=resource_id)
    except ResourceAgent.DoesNotExist:
        raise ResourceNotFoundError(f"Resource with ID={resource_id} does not exist.")
    
    if duration <= timedelta(seconds=0):
        raise ValueError("Duration must be positive.")
    
    exact_end_time = exact_start_time + duration
    
    # CHECK FOR CONFLICTS with SELECT FOR UPDATE (locks the conflicting rows)
    # This ensures no other transaction can create conflicting bookings
    conflicts = Booking.objects.select_for_update().filter(
        resource_id=resource_id,
        start_time__lt=exact_end_time,    # Conflict if it starts before we end
        end_time__gt=exact_start_time      # AND it ends after we start
    ).exists()
    
    if conflicts:
        # FAIL-FAST: Exact slot is occupied, return 409
        # AGV must abort this mission and return to idle state
        raise BookingConflictError(
            f"Exact time slot {exact_start_time} to {exact_end_time} is already occupied. "
            f"Auction result is invalid. AGV must re-bid."
        )
    
    # No conflict! Create the booking for the EXACT slot
    try:
        new_booking = Booking.objects.create(
            resource_id=resource_id,
            agv_id=agv_id,
            start_time=exact_start_time,
            end_time=exact_end_time
        )
        return new_booking
    except DatabaseError as e:
        raise BookingConflictError(f"Failed to create booking due to database error: {str(e)}")


def get_bookings_for_agv(agv_id: int, include_past: bool = False):
    """
    Get all bookings for a specific AGV.
    
    Args:
        agv_id: ID of the AGV
        include_past: If False, only return future/current bookings
        
    Returns:
        QuerySet of Booking objects
    """
    bookings = Booking.objects.filter(agv_id=agv_id).select_related('resource')
    
    if not include_past:
        bookings = bookings.filter(end_time__gte=timezone.now())
    
    return bookings.order_by('start_time')


def get_bookings_for_resource(resource_id: int, start_time=None, end_time=None):
    """
    Get all bookings for a specific resource within a time range.
    
    Args:
        resource_id: ID of the ResourceAgent
        start_time: Optional start of time range
        end_time: Optional end of time range
        
    Returns:
        QuerySet of Booking objects
    """
    bookings = Booking.objects.filter(resource_id=resource_id)
    
    if start_time:
        bookings = bookings.filter(end_time__gte=start_time)
    if end_time:
        bookings = bookings.filter(start_time__lte=end_time)
    
    return bookings.order_by('start_time')


def cancel_booking(booking_id: int):
    """
    Cancel a booking by deleting it.
    
    Args:
        booking_id: ID of the booking to cancel
        
    Returns:
        bool: True if booking was deleted, False if not found
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        booking.delete()
        return True
    except Booking.DoesNotExist:
        return False


def cancel_agv_bookings(agv_id: int, future_only: bool = True):
    """
    Cancel all bookings for a specific AGV.
    
    Args:
        agv_id: ID of the AGV
        future_only: If True, only cancel future bookings
        
    Returns:
        int: Number of bookings cancelled
    """
    bookings = Booking.objects.filter(agv_id=agv_id)
    
    if future_only:
        bookings = bookings.filter(start_time__gt=timezone.now())
    
    count, _ = bookings.delete()
    return count


# ==============================================================================
# Map Service - Graph-based pathfinding with NetworkX
# ==============================================================================

import networkx as nx
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class RouteStep:
    """Represents a single step in a route."""
    node_name: str
    resource_type: str  # CA, LSA, DEPOT, STATION
    pos_x: int = 0
    pos_y: int = 0
    distance_m: float = 0.0
    cumulative_distance_m: float = 0.0
    travel_time_sec: float = 0.0
    cumulative_time_sec: float = 0.0


class MapService:
    """
    Singleton service for map graph management and pathfinding.
    
    Uses NetworkX DiGraph built from ResourceAgent data.
    Provides ideal path calculation using Dijkstra's algorithm.
    """
    
    _instance = None
    _graph: Optional[nx.DiGraph] = None
    _node_data: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MapService, cls).__new__(cls)
        return cls._instance
    
    def load_graph(self) -> bool:
        """
        Load the graph from ResourceAgent database.
        
        Builds a directed graph where:
        - Nodes are CA, DEPOT, STATION resources
        - Edges are LSA resources with from_ca -> to_ca relationships
        - Only ONLINE resources are included
        
        Returns:
            bool: True if graph was successfully loaded, False otherwise
        """
        try:
            self._graph = nx.DiGraph()
            self._node_data = {}
            
            # Load nodes (CA, DEPOT, STATION)
            nodes = ResourceAgent.objects.filter(
                resource_type__in=['CA', 'DEPOT', 'STATION'],
                status='ONLINE'
            )
            
            for node in nodes:
                self._graph.add_node(node.name)
                self._node_data[node.name] = {
                    'resource_type': node.resource_type,
                    'pos_x': node.pos_x,
                    'pos_y': node.pos_y,
                    'id': node.id
                }
            
            # Load edges (LSA)
            edges = ResourceAgent.objects.filter(
                resource_type='LSA',
                status='ONLINE',
                from_ca__isnull=False,
                to_ca__isnull=False
            ).select_related('from_ca', 'to_ca')
            
            for edge in edges:
                self._graph.add_edge(
                    edge.from_ca.name,
                    edge.to_ca.name,
                    weight=edge.distance_m,
                    distance_m=edge.distance_m,
                    base_time_sec=edge.base_time_sec,
                    lsa_name=edge.name,
                    lsa_id=edge.id
                )
            
            return True
        
        except Exception as e:
            print(f"Error loading graph: {e}")
            return False
    
    def reload_graph(self) -> bool:
        """Reload the graph from database (call after map changes)."""
        return self.load_graph()
    
    def get_ideal_path(
        self, 
        start_node: str, 
        end_node: str,
        agv_speed_m_per_sec: float = 1.0
    ) -> Optional[List[RouteStep]]:
        """
        Calculate the ideal (shortest) path between two nodes using Dijkstra.
        
        Args:
            start_node: Name of the starting node (e.g., "CA-01")
            end_node: Name of the destination node (e.g., "STATION-A")
            agv_speed_m_per_sec: AGV speed for time calculation (default 1.0 m/s)
            
        Returns:
            List[RouteStep]: Sequence of route steps with distances and times
            None: If no path exists or graph not loaded
        """
        if self._graph is None:
            print("Graph not loaded. Call load_graph() first.")
            return None
        
        if start_node not in self._graph:
            print(f"Start node '{start_node}' not found in graph")
            return None
        
        if end_node not in self._graph:
            print(f"End node '{end_node}' not found in graph")
            return None
        
        try:
            # Use Dijkstra to find shortest path
            path = nx.shortest_path(
                self._graph, 
                source=start_node, 
                target=end_node, 
                weight='weight'
            )
            
            # Build RouteStep list
            route_steps: List[RouteStep] = []
            cumulative_distance = 0.0
            cumulative_time = 0.0
            
            for i, node_name in enumerate(path):
                node_info = self._node_data.get(node_name, {})
                
                # Get edge info if not the last node
                step_distance = 0.0
                step_time = 0.0
                
                if i < len(path) - 1:
                    next_node = path[i + 1]
                    edge_data = self._graph.get_edge_data(node_name, next_node)
                    if edge_data:
                        step_distance = edge_data.get('distance_m', 0.0)
                        step_time = step_distance / agv_speed_m_per_sec if agv_speed_m_per_sec > 0 else 0.0
                        cumulative_distance += step_distance
                        cumulative_time += step_time
                
                step = RouteStep(
                    node_name=node_name,
                    resource_type=node_info.get('resource_type', 'UNKNOWN'),
                    pos_x=node_info.get('pos_x', 0),
                    pos_y=node_info.get('pos_y', 0),
                    distance_m=step_distance,
                    cumulative_distance_m=cumulative_distance,
                    travel_time_sec=step_time,
                    cumulative_time_sec=cumulative_time
                )
                route_steps.append(step)
            
            return route_steps
        
        except nx.NetworkXNoPath:
            print(f"No path exists between '{start_node}' and '{end_node}'")
            return None
        except Exception as e:
            print(f"Error calculating path: {e}")
            return None
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the current graph."""
        if self._graph is None:
            return {'error': 'Graph not loaded'}
        
        return {
            'num_nodes': self._graph.number_of_nodes(),
            'num_edges': self._graph.number_of_edges(),
            'is_connected': nx.is_weakly_connected(self._graph),
            'nodes': list(self._graph.nodes()),
        }


# Singleton instance (initialize on import)
map_service = MapService()
