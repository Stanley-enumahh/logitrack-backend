from django.core.exceptions import ValidationError
from .models import Order


# Which statuses can move to which next statuses
VALID_TRANSITIONS = {
    Order.Status.PENDING: [Order.Status.ASSIGNED, Order.Status.CANCELLED],
    Order.Status.ASSIGNED: [Order.Status.PICKED_UP, Order.Status.CANCELLED],
    Order.Status.PICKED_UP: [Order.Status.EN_ROUTE, Order.Status.FAILED],
    Order.Status.EN_ROUTE: [Order.Status.AWAITING_CONFIRMATION, Order.Status.FAILED],
    Order.Status.AWAITING_CONFIRMATION: [Order.Status.DELIVERED, Order.Status.DISPUTED],
    Order.Status.DELIVERED: [],
    Order.Status.DISPUTED: [],
    Order.Status.FAILED: [],
    Order.Status.CANCELLED: [],
}


def transition_order_status(order, new_status, actor=None, latitude=None, longitude=None, note=''):
    """
    Validates the transition, updates the order, and writes an
    OrderStatusEvent — the single place this should ever happen.
    """
    from tracking.models import OrderStatusEvent
    from notifications.services import notify_dispatchers
    from notifications.models import Notification

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition from '{order.status}' to '{new_status}'."
        )

    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])

    OrderStatusEvent.objects.create(
        order=order,
        status=new_status,
        actor=actor,
        latitude=latitude,
        longitude=longitude,
        note=note,
    )

    if new_status == Order.Status.DELIVERED:
        notify_dispatchers(
            Notification.NotificationType.DELIVERED,
            title='Order delivered',
            message=f'{order.order_number} was delivered successfully',
            order=order,
        )
    elif new_status == Order.Status.FAILED:
        notify_dispatchers(
            Notification.NotificationType.FAILED,
            title='Delivery failed',
            message=f'{order.order_number} could not be delivered' + (f' — {note}' if note else ''),
            order=order,
        )

    return order