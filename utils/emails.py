import random
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings


def generate_otp():
    return str(random.randint(10000, 99999))

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
    
    
    
    
# For email sending
def send_verification_email(email, code):
    subject = "Verify your email"
    message = f""" 
     Your verification code is: {code}
     This code will expire in 10 minutes.
      """
    send_mail( subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False,)


def send_reset_password_email(email, code):
    subject = "Reset your password"
    message = f"""
     Your password reset code is: {code}
ss
     This code will expire in 10 minutes.
   """
    send_mail( subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False,)