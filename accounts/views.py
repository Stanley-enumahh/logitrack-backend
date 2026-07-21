from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, CreateDriverSerializer, UserSerializer
from .permissions import IsDispatcher
from .models import User
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from .models import DispatcherInvite
from .serializers import SendInviteSerializer, AcceptInviteSerializer
from .emails import send_invite_email
from django.utils import timezone
from .emails import send_verification_email

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'
    rate = '5/min' 

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

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



class VerifyEmailView(APIView):
    """
    Public — activates the account when the emailed token matches.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        try:
            user = User.objects.get(verification_token=token)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid or expired verification link.'}, status=400)

        if user.is_verified:
            return Response({'detail': 'Account already verified.'}, status=400)

        user.is_verified = True
        user.save(update_fields=['is_verified'])

        return Response({'message': 'Email verified. You can now log in.'})


class ResendVerificationView(APIView):
    """
    Public — resend the verification email if the user lost it.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email, role=User.Role.DISPATCHER)
        except User.DoesNotExist:
            # Don't reveal whether the email exists — avoid account enumeration
            return Response({'message': 'If that account exists, a verification email has been sent.'})

        if user.is_verified:
            return Response({'message': 'This account is already verified.'})

        user.verification_sent_at = timezone.now()
        user.save(update_fields=['verification_sent_at'])
        send_verification_email(user)

        return Response({'message': 'If that account exists, a verification email has been sent.'})   
    


class SendInviteView(APIView):
    """
    Dispatcher-only: invite a new dispatcher by email.
    """
    permission_classes = [IsDispatcher]

    def post(self, request):
        serializer = SendInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite = DispatcherInvite.objects.create(
            email=serializer.validated_data['email'],
            invited_by=request.user,
        )
        send_invite_email(invite)

        return Response({'message': f"Invite sent to {invite.email}."}, status=201)


class AcceptInviteView(generics.CreateAPIView):
    """
    Public — no authentication required. Completes signup using
    a valid, unused invite token.
    """
    serializer_class = AcceptInviteSerializer
    permission_classes = [permissions.AllowAny]    