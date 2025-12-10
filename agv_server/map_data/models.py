"""Models for storing AGV map data."""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .constants import MapConstants
from .exceptions import InvalidDirectionException


class MapDataManager(models.Manager):
    """Custom manager for MapData model."""

    def get_or_create_default(self):
        """Get or create the default map data instance."""
        return self.get_or_create(id=1)

    def update_node_count(self, count: int):
        """Update the node count in map data."""
        map_data, _ = self.get_or_create_default()
        map_data.node_count = count
        map_data.save()
        return map_data


class MapData(models.Model):
    """
    Stores general map information.
    Currently only stores the total number of nodes in the map.
    """

    node_count = models.IntegerField(
        default=MapConstants.DEFAULT_NODE_COUNT,
        validators=[MinValueValidator(0)],
        help_text="Total number of nodes in the map",
    )

    objects = MapDataManager()

    class Meta:
        verbose_name = "Map Data"
        verbose_name_plural = "Map Data"

    def __str__(self):
        return f"Map with {self.node_count} nodes"


class ConnectionManager(models.Manager):
    """Custom manager for Connection model."""

    def get_connections_for_node(self, node_id: int):
        """Get all connections for a specific node."""
        return self.filter(models.Q(node1=node_id) | models.Q(node2=node_id))

    def get_distance(self, node1: int, node2: int):
        """Get distance between two nodes."""
        try:
            connection = self.get(node1=node1, node2=node2)
            return connection.distance
        except self.model.DoesNotExist:
            return None

    def bulk_create_connections(self, connections: list):
        """Bulk create connections after clearing existing ones."""
        self.all().delete()
        return self.bulk_create(connections)


class Connection(models.Model):
    """
    Represents a connection between two nodes in the map.
    Stores the distance between connected nodes.
    A value of 10000 in the CSV indicates no connection.
    """

    node1 = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Starting node of the connection"
    )
    node2 = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Ending node of the connection"
    )
    distance = models.FloatField(
        validators=[MinValueValidator(0)], help_text="Distance between the nodes"
    )

    objects = ConnectionManager()

    class Meta:
        verbose_name = "Connection"
        verbose_name_plural = "Connections"
        unique_together = ["node1", "node2"]
        indexes = [
            models.Index(fields=["node1"]),
            models.Index(fields=["node2"]),
        ]

    def __str__(self):
        return f"{self.node1} connects to {self.node2} (distance: {self.distance})"


class DirectionManager(models.Manager):
    """Custom manager for Direction model."""

    def get_direction(self, from_node: int, to_node: int):
        """Get direction from one node to another."""
        try:
            direction = self.get(node1=from_node, node2=to_node)
            return direction.direction
        except self.model.DoesNotExist:
            return None

    def get_directions_for_node(self, node_id: int):
        """Get all directions from a specific node."""
        return self.filter(node1=node_id)

    def bulk_create_directions(self, directions: list):
        """Bulk create directions after clearing existing ones."""
        self.all().delete()
        return self.bulk_create(directions)


class Direction(models.Model):
    """
    Represents the directional relationship between two nodes.
    The direction value indicates the cardinal direction from node1 to node2:
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4
    A value of 10000 in the CSV indicates no direction (no connection).
    """

    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

    DIRECTION_CHOICES = {
        NORTH: "North",
        EAST: "East",
        SOUTH: "South",
        WEST: "West",
    }

    node1 = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Reference node (starting point)"
    )
    node2 = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Target node (ending point)"
    )
    direction = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        choices=DIRECTION_CHOICES,
        help_text="Cardinal direction from node1 to node2 (1=North, 2=East, 3=South, 4=West)",
    )

    objects = DirectionManager()

    class Meta:
        verbose_name = "Direction"
        verbose_name_plural = "Directions"
        unique_together = ["node1", "node2"]
        indexes = [
            models.Index(fields=["node1"]),
            models.Index(fields=["node2"]),
        ]

    def __str__(self):
        direction_name = dict(self.DIRECTION_CHOICES)[self.direction]
        return f"Node {self.node2} is {direction_name} of node {self.node1}"

    @classmethod
    def validate_direction_value(cls, value: int):
        """Validate that direction value is within acceptable range."""
        if not (1 <= value <= 4):
            raise InvalidDirectionException(
                f"Invalid direction value {value}. Must be between 1 and 4."
            )
        return value

    def get_direction_name(self) -> str:
        """Get the human-readable direction name."""
        return dict(self.DIRECTION_CHOICES).get(self.direction, "Unknown")
