from django.urls import path
from .views import SubmitProofOfDeliveryView, ProofOfDeliveryDetailView

from .views import SubmitLocationPingView

from .views import PublicOrderTrackingView

from .views import OrderStatusEventListView

urlpatterns = [
    path('orders/<int:pk>/proof-of-delivery/', SubmitProofOfDeliveryView.as_view(), name='submit_pod'),
    path('orders/<int:order_pk>/proof-of-delivery/view/', ProofOfDeliveryDetailView.as_view(), name='view_pod'),
    path('location-ping/', SubmitLocationPingView.as_view(), name='submit_location_ping'),
    path('public/<uuid:tracking_token>/', PublicOrderTrackingView.as_view(), name='public_tracking'),
    path('orders/<int:order_pk>/events/', OrderStatusEventListView.as_view(), name='order_events'),
]