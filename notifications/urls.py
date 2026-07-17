from django.urls import path
from .views import NotificationListView, UnreadCountView, MarkAllReadView, MarkOneReadView

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification_list'),
    path('unread-count/', UnreadCountView.as_view(), name='unread_count'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='mark_all_read'),
    path('<int:pk>/mark-read/', MarkOneReadView.as_view(), name='mark_one_read'),
]