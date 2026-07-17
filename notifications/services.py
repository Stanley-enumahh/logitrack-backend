from accounts.models import User
from .models import Notification


def notify_dispatchers(notification_type, title, message, order=None):
    """
    Fans a notification out to every dispatcher. Simple for now —
    if you ever have many dispatchers and want per-user targeting,
    this is the one place to change.
    """
    dispatchers = User.objects.filter(role=User.Role.DISPATCHER)
    Notification.objects.bulk_create([
        Notification(
            recipient=dispatcher,
            notification_type=notification_type,
            title=title,
            message=message,
            order=order,
        )
        for dispatcher in dispatchers
    ])