from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView, CreateDriverView, MeView, DriverListView, DriverAvailabilityView

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('drivers/create/', CreateDriverView.as_view(), name='create_driver'),
    path('drivers/', DriverListView.as_view(), name='driver_list'),
    path('me/', MeView.as_view(), name='me'),
    path('drivers/availability/', DriverAvailabilityView.as_view(), name='driver_availability'),
]