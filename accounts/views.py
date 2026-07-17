from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, CreateDriverSerializer, UserSerializer
from .permissions import IsDispatcher
from .models import User
from rest_framework.response import Response


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CreateDriverView(generics.CreateAPIView):
    """
    Dispatcher-only endpoint to create a driver account.
    """
    serializer_class = CreateDriverSerializer
    permission_classes = [IsDispatcher]


class MeView(generics.RetrieveAPIView):
    """
    Returns the currently authenticated user's profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class DriverListView(generics.ListAPIView):
    """
    Dispatcher-only: list all drivers (for assignment UI).
    """
    serializer_class = UserSerializer
    permission_classes = [IsDispatcher]
    queryset = User.objects.filter(role=User.Role.DRIVER)
    
from rest_framework.views import APIView

class DriverAvailabilityView(APIView):
    permission_classes = [IsDispatcher]

    def get(self, request):
        from .models import DriverProfile
        available = DriverProfile.objects.filter(is_available=True).count()
        total = DriverProfile.objects.count()
        return Response({'available': available, 'offline': total - available, 'total': total})