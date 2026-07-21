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
    
     

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_verified:
            raise serializers.ValidationError(
                "Please verify your email before logging in."
            )
        return data       
    
    
class SendInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value


class AcceptInviteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    token = serializers.UUIDField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone_number', 'token']
        extra_kwargs = {'email': {'required': False}}

    def validate(self, data):
        from .models import DispatcherInvite
        try:
            invite = DispatcherInvite.objects.get(token=data['token'], is_used=False)
        except DispatcherInvite.DoesNotExist:
            raise serializers.ValidationError("Invalid or already-used invite link.")

        if invite.is_expired():
            raise serializers.ValidationError("This invite link has expired.")

        data['invite'] = invite
        return data

    def create(self, validated_data):
        invite = validated_data.pop('invite')
        validated_data.pop('token')

        user = User(
            username=validated_data['username'],
            email=invite.email,
            phone_number=validated_data.get('phone_number', ''),
            role=User.Role.DISPATCHER,
            is_verified=True,  # accepting the invite IS the verification
        )
        user.set_password(validated_data['password'])
        user.save()

        invite.is_used = True
        invite.save(update_fields=['is_used'])

        return user    