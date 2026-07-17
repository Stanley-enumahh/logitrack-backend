from django.urls import path
from .views import OrderListCreateView, OrderDetailView, AssignDriverView, UpdateOrderStatusView, PublicOrderCreateView, DispatcherOverviewView

urlpatterns = [
    path('', OrderListCreateView.as_view(), name='order_list_create'),
    path('public/create/', PublicOrderCreateView.as_view(), name='public_order_create'),
    path('overview/', DispatcherOverviewView.as_view(), name='dispatcher_overview'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/assign-driver/', AssignDriverView.as_view(), name='assign_driver'),
    path('<int:pk>/update-status/', UpdateOrderStatusView.as_view(), name='update_status'),
]