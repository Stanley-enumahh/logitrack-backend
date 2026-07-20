from django.shortcuts import render

# Create your views here.
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from orders.models import Order
from orders.permissions import IsAssignedDriverOrDispatcher
from orders.services import transition_order_status
from .models import ProofOfDelivery


from .serializers import (
    CreateProofOfDeliverySerializer,
    ProofOfDeliverySerializer,
    LocationPingSerializer,
    PublicOrderTrackingSerializer,
    InternalStatusEventSerializer,
    PublicProofOfDeliverySerializer,
    ConfirmDeliverySerializer,
)

from accounts.permissions import IsDriver

from rest_framework.permissions import AllowAny
from orders.models import Order

from django.utils import timezone

class SubmitProofOfDeliveryView(APIView):
    """
    Dispatcher or assigned driver submits proof of delivery.
    This also transitions the order status to 'delivered' —
    only valid if the order is currently 'en_route'.
    """
    permission_classes = [permissions.IsAuthenticated, IsAssignedDriverOrDispatcher]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk)
        self.check_object_permissions(request, order)

        if hasattr(order, 'proof_of_delivery'):
            return Response(
                {'detail': 'Proof of delivery already submitted for this order.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        serializer = CreateProofOfDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pod = serializer.save(order=order)

        try:
          transition_order_status(
        order,
        new_status=Order.Status.AWAITING_CONFIRMATION,
        actor=request.user,
        latitude=serializer.validated_data.get('latitude'),
        longitude=serializer.validated_data.get('longitude'),
        note='Proof of delivery submitted, awaiting customer confirmation',
          )
        except DjangoValidationError as e:
          pod.delete()
          return Response({'detail': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)

        return Response(ProofOfDeliverySerializer(pod).data, status=http_status.HTTP_201_CREATED)


class ProofOfDeliveryDetailView(generics.RetrieveAPIView):
    """
    View POD for a specific order (dispatcher or assigned driver).
    """
    serializer_class = ProofOfDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'order_pk'

    def get_object(self):
        order = generics.get_object_or_404(Order, pk=self.kwargs['order_pk'])
        user = self.request.user
        if user.role == 'driver' and order.assigned_driver_id != user.id:
            self.permission_denied(self.request)
        return generics.get_object_or_404(ProofOfDelivery, order=order)



class SubmitLocationPingView(generics.CreateAPIView):
    """
    Driver pushes their current location. Updates both:
    - LocationPing (historical log, for path reconstruction)
    - DriverProfile.current_latitude/longitude (fast lookup snapshot)

    `order` is optional in the payload — include it when actively
    delivering, so the ping is tied to that order's tracking view.
    """
    serializer_class = LocationPingSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        ping = serializer.save(driver=self.request.user)

        driver_profile = getattr(self.request.user, 'driver_profile', None)
        if driver_profile:
            driver_profile.current_latitude = ping.latitude
            driver_profile.current_longitude = ping.longitude
            driver_profile.last_location_update = ping.timestamp
            driver_profile.save(update_fields=[
                'current_latitude', 'current_longitude', 'last_location_update',
            ])


class PublicOrderTrackingView(generics.RetrieveAPIView):
    """
    No authentication required. Looked up by tracking_token (UUID),
    not the order's primary key, so it can't be enumerated/guessed.
    """
    serializer_class = PublicOrderTrackingSerializer
    permission_classes = [AllowAny]
    lookup_field = 'tracking_token'
    lookup_url_kwarg = 'tracking_token'
    queryset = Order.objects.all()            
    
    
class OrderStatusEventListView(generics.ListAPIView):
    """
    Full internal timeline for an order — includes actor and coordinates,
    unlike the public-facing timeline.
    """
    serializer_class = InternalStatusEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        order = generics.get_object_or_404(Order, pk=self.kwargs['order_pk'])
        user = self.request.user
        if user.role == 'driver' and order.assigned_driver_id != user.id:
            self.permission_denied(self.request)
        return order.status_events.all().order_by('timestamp')    


class ConfirmDeliveryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, tracking_token):
        from orders.models import Order
        from orders.services import transition_order_status
        from django.core.exceptions import ValidationError as DjangoValidationError

        order = generics.get_object_or_404(Order, tracking_token=tracking_token)

        pod = getattr(order, 'proof_of_delivery', None)
        if not pod:
            return Response({'detail': 'No delivery to confirm yet.'}, status=400)

        if pod.confirmation_status != ProofOfDelivery.ConfirmationStatus.PENDING:
            return Response(
                {'detail': 'This delivery has already been confirmed or disputed.'},
                status=400,
            )

        serializer = ConfirmDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data['confirmed']:
            pod.confirmation_status = ProofOfDelivery.ConfirmationStatus.CONFIRMED
            new_order_status = Order.Status.DELIVERED
            note = f'Delivery confirmed by {data["confirmed_by_name"]}'
        else:
            pod.confirmation_status = ProofOfDelivery.ConfirmationStatus.DISPUTED
            pod.dispute_reason = data.get('dispute_reason', '')
            new_order_status = Order.Status.DISPUTED
            note = f'{data["confirmed_by_name"]}: {data.get("dispute_reason", "")}'

            from notifications.services import notify_dispatchers
            from notifications.models import Notification
            notify_dispatchers(
                Notification.NotificationType.FAILED,
                title='Delivery disputed',
                message=f'{order.order_number}: {data["confirmed_by_name"]} reports non-receipt',
                order=order,
            )

        pod.confirmed_by_name = data['confirmed_by_name']
        pod.confirmed_at = timezone.now()
        pod.save(update_fields=['confirmation_status', 'dispute_reason', 'confirmed_by_name', 'confirmed_at'])

        try:
            transition_order_status(order, new_order_status, note=note)
        except DjangoValidationError as e:
            return Response({'detail': str(e)}, status=400)

        return Response(PublicProofOfDeliverySerializer(pod).data) 