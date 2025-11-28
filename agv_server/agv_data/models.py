from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q
from order_data.models import Order


class ResourceAgent(models.Model):
    """
    Represents a resource in the D-MAS system.
    Can be a Crossroad Agent (CA), Logical Segment Agent (LSA),
    Depot station, or Pickup/Delivery station.
    
    For map visualization and pathfinding:
    - Nodes: CA, DEPOT, STATION (have pos_x, pos_y)
    - Edges: LSA (connect from_ca to to_ca, have distance_m, base_time_sec)
    """
    class ResourceType(models.TextChoices):
        CROSSROAD = 'CA', 'Crossroad Agent'
        SEGMENT = 'LSA', 'Logical Segment Agent'
        DEPOT = 'DEPOT', 'Depot Station'
        STATION = 'STATION', 'Pickup/Delivery Station'

    class StatusType(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        OFFLINE = 'OFFLINE', 'Offline (Maintenance)'

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique identifier, e.g., 'CA-01', 'LSA_01_02', 'DEPOT-01', 'STATION-A'"
    )
    resource_type = models.CharField(
        max_length=10,
        choices=ResourceType.choices,
        help_text="Resource type (CA, LSA, DEPOT, or STATION)"
    )
    status = models.CharField(
        max_length=10,
        choices=StatusType.choices,
        default=StatusType.ONLINE,
        help_text="Resource status (ONLINE or OFFLINE for maintenance)"
    )

    # Position fields (for nodes: CA, DEPOT, STATION)
    pos_x = models.IntegerField(
        default=0,
        help_text="X coordinate for UI visualization (pixels)"
    )
    pos_y = models.IntegerField(
        default=0,
        help_text="Y coordinate for UI visualization (pixels)"
    )

    # Edge/Connection fields (for LSA only)
    from_ca = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='edges_out',
        null=True,
        blank=True,
        limit_choices_to=~Q(resource_type='LSA'),
        help_text="(LSA only) Starting node of this edge"
    )
    to_ca = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='edges_in',
        null=True,
        blank=True,
        limit_choices_to=~Q(resource_type='LSA'),
        help_text="(LSA only) Ending node of this edge"
    )
    distance_m = models.FloatField(
        default=0.0,
        help_text="(LSA only) Distance in meters"
    )
    base_time_sec = models.FloatField(
        default=0.0,
        help_text="(LSA only) Ideal travel time in seconds"
    )

    class Meta:
        verbose_name = "Resource Agent"
        verbose_name_plural = "Resource Agents"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_resource_type_display()})"


class Booking(models.Model):
    """
    Represents a reservation booking in the Reservation Table.
    Each booking reserves a resource (CA/LSA) for a specific time slot.
    """
    resource = models.ForeignKey(
        ResourceAgent,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="Reserved resource (CA/LSA)"
    )
    agv_id = models.BigIntegerField(
        db_index=True,
        help_text="AGV making the reservation"
    )
    start_time = models.DateTimeField(help_text="Start time of resource occupation")
    end_time = models.DateTimeField(help_text="End time of resource release")

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        indexes = [
            models.Index(fields=['resource', 'start_time']),
            models.Index(fields=['resource', 'end_time']),
        ]
        ordering = ['start_time']

    def __str__(self):
        return f"AGV {self.agv_id} @ {self.resource.name} [{self.start_time} - {self.end_time}]"

class Agv(models.Model):
    """
    Represents an AGV in the SSI-DMAS-ET system.
    
    SSI-DMAS-ET: Sequential Single-Item Auction with Delegate Multi-Agent System 
    and Energy-Time Optimization.
    
    The system uses:
    - Auction-based task allocation (not DSPA path planning)
    - Reservation Table for conflict-free resource allocation
    - DMAS-ET exploring ant for cost calculation (energy + time)
    - Intention ant for actual booking (pending implementation)
    """

    # Motion state choices
    IDLE = 0  # No mission to execute
    MOVING = 1  # On way to next reserved point
    WAITING = 2  # Stopped at current point

    MOTION_STATE_CHOICES = {IDLE: "Idle", MOVING: "Moving", WAITING: "Waiting"}

    # Journey phase choices (used for load calculation in bidding)
    OUTBOUND = 0  # Moving from parking → storage → workstation (may carry load)
    INBOUND = 1  # Moving from workstation → parking (empty)

    JOURNEY_PHASE_CHOICES = {OUTBOUND: "Outbound", INBOUND: "Inbound"}

    # Direction change choices (for physical AGV control)
    GO_STRAIGHT = 0
    TURN_AROUND = 1
    TURN_LEFT = 2
    TURN_RIGHT = 3

    DIRECTION_CHANGE_CHOICES = {
        GO_STRAIGHT: "Go straight",
        TURN_AROUND: "Turn around",
        TURN_LEFT: "Turn left",
        TURN_RIGHT: "Turn right",
    }

    # ========================================
    # CORE FIELDS (Used by SSI-DMAS-ET)
    # ========================================
    
    agv_id = models.BigIntegerField(primary_key=True)
    preferred_parking_node = models.IntegerField(
        help_text="Preferred parking point for AGV"
    )

    # Navigation fields
    current_node = models.IntegerField(
        null=True,
        help_text="Current position: node where AGV is located or last left",
    )
    next_node = models.IntegerField(
        null=True, 
        help_text="Next node to visit"
    )
    reserved_node = models.IntegerField(
        null=True, 
        help_text="Reserved node (booked via Reservation Table)"
    )
    previous_node = models.IntegerField(
        null=True, 
        help_text="Last node visited (for direction calculation)"
    )

    # Physical control
    direction_change = models.IntegerField(
        choices=DIRECTION_CHANGE_CHOICES,
        null=True,
        help_text="Direction to turn after reaching a node",
    )

    # State management
    motion_state = models.IntegerField(
        choices=MOTION_STATE_CHOICES,
        default=IDLE,
        help_text="Current motion state",
    )

    journey_phase = models.IntegerField(
        choices=JOURNEY_PHASE_CHOICES,
        default=OUTBOUND,
        help_text="Journey phase (affects load weight in energy calculation)",
    )

    # Task management
    active_order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_agv",
        help_text="Currently executing order (assigned by auction winner selection)",
    )

    # Path tracking (used by BiddingService for J1 calculation)
    remaining_path = ArrayField(
        models.IntegerField(),
        help_text="Remaining nodes to visit (used for calculating J1 cost in busy AGVs)",
        default=list,
        size=None,
    )

    # ========================================
    # DEPRECATED FIELDS (DSPA - Not used by SSI-DMAS-ET)
    # ========================================
    # These fields are kept for backward compatibility but not used in current algorithm.
    # Can be removed in future migration after confirming no dependencies.
    
    # DSPA deadlock resolution (replaced by Reservation Table)
    spare_flag = models.BooleanField(
        default=False,
        help_text="[DEPRECATED] DSPA spare flag - not used in SSI-DMAS-ET",
    )
    backup_nodes = models.JSONField(
        default=dict,
        help_text="[DEPRECATED] DSPA backup nodes - not used in SSI-DMAS-ET",
    )
    waiting_for_deadlock_resolution = models.BooleanField(
        default=False,
        help_text="[DEPRECATED] DSPA deadlock tracking - not used in SSI-DMAS-ET",
    )
    deadlock_partner_agv_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="[DEPRECATED] DSPA deadlock partner - not used in SSI-DMAS-ET",
    )

    # DSPA path fields (replaced by dynamic route planning + Reservation Table)
    initial_path = ArrayField(
        models.IntegerField(),
        help_text="[DEPRECATED] DSPA initial path - not used in SSI-DMAS-ET",
        default=list,
        size=None,
    )
    outbound_path = ArrayField(
        models.IntegerField(),
        help_text="[DEPRECATED] DSPA outbound path - not used in SSI-DMAS-ET",
        default=list,
        size=None,
    )
    inbound_path = ArrayField(
        models.IntegerField(),
        help_text="[DEPRECATED] DSPA inbound path - not used in SSI-DMAS-ET",
        default=list,
        size=None,
    )
    common_nodes = ArrayField(
        models.IntegerField(),
        help_text="[DEPRECATED] DSPA common nodes - not used in SSI-DMAS-ET",
        default=list,
        size=None,
    )
    adjacent_common_nodes = ArrayField(
        models.IntegerField(),
        help_text="[DEPRECATED] DSPA adjacent common nodes - not used in SSI-DMAS-ET",
        default=list,
        size=None,
    )

    def save(self, *args, **kwargs):
        """
        Override the save method to send WebSocket updates whenever an AGV instance is saved.
        This replaces the post_save signal handler with equivalent functionality.
        """
        # Call the parent class's save method to save the model
        super().save(*args, **kwargs)

        # Import here to avoid circular imports
        from .serializers import AGVSerializer
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        # Serialize the AGV instance
        serializer = AGVSerializer(self)
        agv_data = serializer.data

        # Get the channel layer
        channel_layer = get_channel_layer()

        # Send message to the WebSocket group
        async_to_sync(channel_layer.group_send)(
            "agv_group",  # Group name for AGV updates
            {
                "type": "agv_message",
                "message": {"type": "agv_update", "data": agv_data},
            },
        )

    class Meta:
        verbose_name = "AGV"
        verbose_name_plural = "AGVs"
        ordering = ["agv_id"]

    def __str__(self):
        return f"AGV {self.agv_id} likes to park at {self.preferred_parking_node} and is currently at {self.current_node} with state {self.get_motion_state_display()}."


# For every field that has choices set, the object will have a get_FOO_display() method, where FOO is the name of the field. This method returns the “human-readable” value of the field.
