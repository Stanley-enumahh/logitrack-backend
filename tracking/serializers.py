from rest_framework import serializers
from .models import ProofOfDelivery
from .models import LocationPing
from orders.models import Order
from .models import OrderStatusEvent, ProofOfDelivery, LocationPing


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = [
            'id', 'order', 'photo', 'signature',
            'recipient_name', 'latitude', 'longitude', 'captured_at',
        ]
        read_only_fields = ['id', 'order', 'captured_at']


class CreateProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = ['photo', 'signature', 'recipient_name', 'latitude', 'longitude']

    def validate(self, data):
        if not data.get('photo') and not data.get('signature'):
            raise serializers.ValidationError(
                "At least one of photo or signature is required."
            )
        return data
    
    
class LocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPing
        fields = ['id', 'order', 'latitude', 'longitude', 'timestamp']
        read_only_fields = ['id', 'timestamp']

    def validate_order(self, order):
        if order is not None:
            request = self.context['request']
            if order.assigned_driver_id != request.user.id:
                raise serializers.ValidationError("This order is not assigned to you.")
        return order    
 

class PublicStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusEvent
        fields = ['status', 'timestamp', 'note']


class PublicProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = ['photo', 'signature', 'recipient_name', 'captured_at']


class PublicOrderTrackingSerializer(serializers.ModelSerializer):
    """
    Customer-facing view via tracking_token. Deliberately excludes
    internal fields: driver personal info, dispatcher notes,
    raw coordinates beyond what's needed to show live location.
    """
    timeline = serializers.SerializerMethodField()
    driver_location = serializers.SerializerMethodField()
    proof_of_delivery = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'order_number', 'status', 'customer_name',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'dropoff_address', 'dropoff_latitude', 'dropoff_longitude',
            'created_at', 'timeline', 'driver_location', 'proof_of_delivery',
        ]

    def get_timeline(self, order):
        events = order.status_events.all().order_by('timestamp')
        return PublicStatusEventSerializer(events, many=True).data

    def get_driver_location(self, order):
        active_statuses = [Order.Status.ASSIGNED, Order.Status.PICKED_UP, Order.Status.EN_ROUTE]
        if order.status not in active_statuses:
            return None
        driver = order.assigned_driver
        if not driver or not hasattr(driver, 'driver_profile'):
            return None
        profile = driver.driver_profile
        if profile.current_latitude is None:
            return None
        return {
            'latitude': profile.current_latitude,
            'longitude': profile.current_longitude,
            'last_updated': profile.last_location_update,
        }

    def get_proof_of_delivery(self, order):
        if order.status != Order.Status.DELIVERED:
            return None
        pod = getattr(order, 'proof_of_delivery', None)
        if not pod:
            return None
        return PublicProofOfDeliverySerializer(pod).data    
    


class InternalStatusEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, default=None)

    class Meta:
        model = OrderStatusEvent
        fields = ['id', 'status', 'actor_username', 'latitude', 'longitude', 'note', 'timestamp']  
        

class Meta:
    model = Order
    fields = [
        'order_number', 'status', 'customer_name',
        'pickup_address', 'pickup_latitude', 'pickup_longitude',
        'dropoff_address', 'dropoff_latitude', 'dropoff_longitude',
        'created_at', 'timeline', 'driver_location', 'proof_of_delivery',
    ]          