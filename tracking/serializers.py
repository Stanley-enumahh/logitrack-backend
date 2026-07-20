from rest_framework import serializers
from .models import ProofOfDelivery
from .models import LocationPing
from orders.models import Order
from .models import OrderStatusEvent, ProofOfDelivery, LocationPing
from django.core.exceptions import ValidationError as DjangoValidationError



class ProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = [
            'id', 'order', 'photo', 'signature',
            'recipient_name', 'latitude', 'longitude', 'captured_at',
        ]
        read_only_fields = ['id', 'order', 'captured_at']


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']


class CreateProofOfDeliverySerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = ProofOfDelivery
        fields = ['photo', 'signature', 'recipient_name', 'latitude', 'longitude']

    def _validate_file(self, file_obj, field_name):
        if file_obj.size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"{field_name} must be under 5MB."
            )
        content_type = getattr(file_obj, 'content_type', None)
        if content_type and content_type not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                f"{field_name} must be a JPEG, PNG, or WEBP image."
            )

    def validate_photo(self, value):
        if value:
            self._validate_file(value, 'Photo')
        return value

    def validate_signature(self, value):
        if value:
            self._validate_file(value, 'Signature')
        return value

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
        fields = [
            'photo', 'signature', 'recipient_name', 'captured_at',
            'confirmation_status', 'dispute_reason', 'confirmed_by_name', 'confirmed_at',
        ]


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
        visible_statuses = [
            Order.Status.AWAITING_CONFIRMATION,
            Order.Status.DELIVERED,
            Order.Status.DISPUTED,
    ]
        if order.status not in visible_statuses:
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
    
class ConfirmDeliverySerializer(serializers.Serializer):
    confirmed = serializers.BooleanField()
    confirmed_by_name = serializers.CharField(max_length=150, required=True, allow_blank=False)
    dispute_reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, data):
        if not data['confirmed'] and not data.get('dispute_reason'):
            raise serializers.ValidationError(
                "Please provide a reason if you didn't receive this delivery."
            )
        return data         