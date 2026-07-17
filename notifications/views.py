from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsDispatcher
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsDispatcher]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class UnreadCountView(APIView):
    permission_classes = [IsDispatcher]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})


class MarkAllReadView(APIView):
    permission_classes = [IsDispatcher]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


class MarkOneReadView(APIView):
    permission_classes = [IsDispatcher]

    def post(self, request, pk):
        notification = generics.get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'ok'})