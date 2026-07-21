from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(user):
    verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.verification_token}/"

    subject = "Verify your LogiTrack dispatcher account"
    message = (
        f"Hi {user.username},\n\n"
        f"Please verify your email to activate your dispatcher account:\n"
        f"{verification_url}\n\n"
        f"If you didn't create this account, you can ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    
    
def send_invite_email(invite):
    invite_url = f"{settings.FRONTEND_URL}/accept-invite/{invite.token}/"

    subject = f"{invite.invited_by.username} invited you to join LogiTrack"
    message = (
        f"You've been invited to join LogiTrack as a dispatcher.\n\n"
        f"Click here to set up your account:\n{invite_url}\n\n"
        f"This link expires in 7 days."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.email],
        fail_silently=False,
    )    