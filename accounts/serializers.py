from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, DriverProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT to embed role and user id in the token payload,
    so the frontend can read the role immediately without an extra API call.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['username'] = user.username
        return token


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            'vehicle_type', 'vehicle_plate_number', 'is_available',
            'current_latitude', 'current_longitude', 'last_location_update',
        ]


class UserSerializer(serializers.ModelSerializer):
    driver_profile = DriverProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone_number', 'driver_profile']


class CreateDriverSerializer(serializers.ModelSerializer):
    """
    Used only by dispatchers to create driver accounts.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    vehicle_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    vehicle_plate_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone_number', 'vehicle_type', 'vehicle_plate_number']

    def create(self, validated_data):
        vehicle_type = validated_data.pop('vehicle_type', '')
        vehicle_plate_number = validated_data.pop('vehicle_plate_number', '')
        password = validated_data.pop('password')

        user = User(**validated_data, role=User.Role.DRIVER)
        user.set_password(password)
        user.save()

        DriverProfile.objects.create(
            user=user,
            vehicle_type=vehicle_type,
            vehicle_plate_number=vehicle_plate_number,
        )
        return user