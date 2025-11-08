from rest_framework import serializers
from .models import Agv, ResourceAgent, Booking
from order_data.models import Order


class OrderInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for basic order information needed in AGV responses.
    """

    class Meta:
        model = Order
        fields = (
            "order_id",
            "order_date",
            "start_time",
            "parking_node",
            "storage_node",
            "workstation_node",
        )


class ResourceAgentSerializer(serializers.ModelSerializer):
    """
    Serializer for ResourceAgent model (CA/LSA).
    """
    
    class Meta:
        model = ResourceAgent
        fields = ['id', 'name', 'resource_type']


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking model.
    Includes resource information for detailed responses.
    """
    resource_info = ResourceAgentSerializer(source='resource', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'resource', 'resource_info', 'agv_id', 'start_time', 'end_time']
        read_only_fields = ['id']


class AGVSerializer(serializers.ModelSerializer):
    """
    Serializer for the AGV model that includes active order information.
    """

    # Include order information for API compatibility
    active_order_info = serializers.SerializerMethodField()

    def get_active_order_info(self, obj):
        """
        Get detailed information about the AGV's active order.

        Args:
            obj: The AGV instance being serialized

        Returns:
            dict: Order information or None if no active order
        """
        if obj.active_order:
            return OrderInfoSerializer(obj.active_order).data
        return None

    class Meta:
        model = Agv
        fields = "__all__"
