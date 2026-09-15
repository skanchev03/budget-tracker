from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


def send_verification_email(user, raw_token):
    """
    Sends an email containing the user's email verification link.
    """

    verification_path = reverse(
        "verify-email",
        kwargs={"token": raw_token},
    )

    verification_url = (
        f"{settings.SITE_URL}{verification_path}"
    )

    subject = "Verify your Budget Tracker email"

    text_message = f"""
Hello {user.username},

Thank you for registering with Budget Tracker.

Please verify your email address by clicking the link below:

{verification_url}

This link expires in 24 hours.

If you did not create this account, you can ignore this email.

Best regards,
Budget Tracker
""".strip()

    html_message = render_to_string(
        "users/emails/verify_email.html",
        {
            "user": user,
            "verification_url": verification_url,
        },
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach_alternative(
        html_message,
        "text/html",
    )

    email.send()


def send_two_factor_email(user, raw_code):
    """
    Sends an email containing the user's 2FA verification code.
    """

    subject = "Your Budget Tracker verification code"

    text_message = f"""
Hello {user.username},

Your Budget Tracker verification code is:

{raw_code}

This code expires in 10 minutes.

If you did not attempt to log in, you can ignore this email.

Best regards,
Budget Tracker
""".strip()

    html_message = render_to_string(
        "users/emails/two_factor_code.html",
        {
            "user": user,
            "raw_code": raw_code,
        },
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach_alternative(
        html_message,
        "text/html",
    )

    email.send()