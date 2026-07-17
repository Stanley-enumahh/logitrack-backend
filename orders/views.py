from django.shortcuts import render

# Create your views here.
from django.core.exceptions import ValidationError
from rest_framework import generics, permissions, status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsDispatcher
from accounts.models import User
from .models import Order
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    AssignDriverSerializer, UpdateStatusSerializer,
)
from .permissions import IsAssignedDriverOrDispatcher
from .services import transition_order_status

from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from .serializers import PublicOrderCreateSerializer

from django.utils import timezone
from django.db.models import Count, Q

from notifications.services import notify_dispatchers
from notifications.models import Notification


class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'assigned_driver']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'dispatcher':
            return Order.objects.all()
        return Order.objects.filter(assigned_driver=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != 'dispatcher':
            raise permissions.PermissionDenied("Only dispatchers can create orders.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        # Return the full order representation, not just the input fields
        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=http_status.HTTP_201_CREATED)

class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsAssignedDriverOrDispatcher]
    queryset = Order.objects.all()


class AssignDriverView(APIView):
    """
    Dispatcher-only: assign a driver to a pending order.
    """
    permission_classes = [IsDispatcher]

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk)
        serializer = AssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            driver = User.objects.get(id=serializer.validated_data['driver_id'], role=User.Role.DRIVER)
        except User.DoesNotExist:
            return Response({'detail': 'Driver not found.'}, status=http_status.HTTP_404_NOT_FOUND)

        order.assigned_driver = driver
        order.save(update_fields=['assigned_driver', 'updated_at'])

        try:
            transition_order_status(order, Order.Status.ASSIGNED, actor=request.user)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data)


class UpdateOrderStatusView(APIView):
    """
    Dispatcher or the assigned driver can update status.
    Enforces valid transitions and writes the audit log entry.
    """
    permission_classes = [permissions.IsAuthenticated, IsAssignedDriverOrDispatcher]

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk)
        self.check_object_permissions(request, order)

        serializer = UpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            transition_order_status(
                order,
                new_status=data['status'],
                actor=request.user,
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                note=data.get('note', ''),
            )
        except ValidationError as e:
            return Response({'detail': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data)


class PublicOrderCreateThrottle(AnonRateThrottle):
    rate = '10/hour'
 
    
class PublicOrderCreateView(generics.CreateAPIView):
    serializer_class = PublicOrderCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [PublicOrderCreateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        notify_dispatchers(
            Notification.NotificationType.NEW_ORDER,
            title='New order placed',
            message=f'{order.customer_name} requested a delivery — {order.order_number}',
            order=order,
        )

        return Response(
            {
                'order_number': order.order_number,
                'tracking_token': order.tracking_token,
                'status': order.status,
                'message': 'Order placed successfully. Use the tracking_token to follow your delivery.',
            },
            status=http_status.HTTP_201_CREATED,
        )

class DispatcherOverviewView(APIView):
    """
    Dispatcher-only. Returns today's order counts, unassigned orders,
    and recent status events for the overview dashboard.
    """
    permission_classes = [IsDispatcher]

    def get(self, request):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        today_orders = Order.objects.filter(created_at__gte=today_start)

        stats = today_orders.aggregate(
            total_today=Count('id'),
            pending=Count('id', filter=Q(status=Order.Status.PENDING)),
            active=Count('id', filter=Q(status__in=[
                Order.Status.ASSIGNED, Order.Status.PICKED_UP, Order.Status.EN_ROUTE
            ])),
            delivered_today=Count('id', filter=Q(status=Order.Status.DELIVERED)),
            urgent=Count('id', filter=Q(priority=Order.Priority.URGENT) & ~Q(status__in=[
                Order.Status.DELIVERED, Order.Status.FAILED, Order.Status.CANCELLED
            ])),
        )

        unassigned = Order.objects.filter(
            status=Order.Status.PENDING
        ).order_by('-priority', 'created_at')[:5]

        return Response({
            'stats': stats,
            'unassigned_orders': OrderSerializer(unassigned, many=True).data,
        })        