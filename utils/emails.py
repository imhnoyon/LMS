from django.core.mail import EmailMessage
import random
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def generate_otp():
    return str(random.randint(100000, 999999))

def otp_expiry(minutes=10):
    return timezone.now() + timedelta(minutes=minutes)

def generate_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "access_token_valid_till": int(
            (timezone.now() + timedelta(minutes=30)).timestamp() * 1000
        ),
        "refresh_token": str(refresh),
    }
    
    
    

def send_verification_email(email, code):
    subject = "Learn Hub | Verify Your Email"

    html_content = render_to_string(
        "emails/email_verification.html",
        {
            "otp_code": code,
            "expiry_minutes": 10,
            "user": {"email": email}
        }
    )

    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.content_subtype = "html"
    email_message.send()




def send_reset_password_email(email, code):
    subject = "Learn Hub | Password Reset"

    html_content = render_to_string(
        "emails/password_reset.html",
        {
            "otp_code": code,
            "expiry_minutes": 10,
            "user": {"email": email},
        }
    )

    message = EmailMessage(
        subject,
        html_content,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )
    message.content_subtype = "html"
    message.send()


# def send_invitation_email(email, organization_name, invitation_token, is_registered):
#     subject = f"Learn Hub | Invitation from {organization_name}"
    
#     frontend_url = getattr(settings, "FRONTEND_URL", "https://lms-web-teal.vercel.app/en/")
    
#     if is_registered:
#         link = f"{frontend_url}/organization-invitation/respond?token={invitation_token}"
#     else:
#         link = f"{frontend_url}/auth/trainer-sign-up?invite_token={invitation_token}&email={email}"

#     html_content = render_to_string(
#         "emails/organization_invitation.html",
#         {
#             "organization_name": organization_name,
#             "invitation_link": link,
#             "is_registered": is_registered,
#             "email": email
#         }
#     )

#     message = EmailMessage(
#         subject,
#         html_content,
#         settings.DEFAULT_FROM_EMAIL,
#         [email],
#     )
#     message.content_subtype = "html"
#     message.send()



def send_invitation_email(email, organization_name, invitation_token, is_registered):
    subject = f"Learn Hub | Invitation from {organization_name}"

    if is_registered:
        link = (
            f"https://lms-web-teal.vercel.app/en/organization-invitation"
            f"?token={invitation_token}"
        )
    else:
        link = (
            f"https://lms-web-teal.vercel.app/en/auth/trainer-sign-up"
            f"?token={invitation_token}&email={email}"
        )

    html_content = render_to_string(
        "emails/organization_invitation.html",
        {
            "organization_name": organization_name,
            "invitation_link": link,
            "is_registered": is_registered,
            "email": email,
        },
    )

    message = EmailMessage(
        subject,
        html_content,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )

    message.content_subtype = "html"
    message.send()