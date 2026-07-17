from rest_framework import serializers
from .models import Order
from accounts.serializers import UserSerializer


class OrderSerializer(serializers.ModelSerializer):
    assigned_driver_detail = UserSerializer(source='assigned_driver', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'tracking_token',
            'customer_name', 'customer_phone', 'customer_email',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'dropoff_address', 'dropoff_latitude', 'dropoff_longitude',
            'status', 'priority',
            'assigned_driver', 'assigned_driver_detail',
            'time_window_start', 'time_window_end',
            'delivery_notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['order_number', 'tracking_token', 'status', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Dispatcher-only. Status always starts as 'pending' regardless of input.
    """
    class Meta:
        model = Order
        fields = [
            'customer_name', 'customer_phone', 'customer_email',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'dropoff_address', 'dropoff_latitude', 'dropoff_longitude',
            'priority', 'time_window_start', 'time_window_end', 'delivery_notes',
        ]


class AssignDriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
class PublicOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'customer_name', 'customer_phone', 'customer_email',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'dropoff_address', 'dropoff_latitude', 'dropoff_longitude',
            'delivery_notes',
        ]
   