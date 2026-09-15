from datetime import date, timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Currency

from apps.users.emails import send_verification_email
from apps.users.forms import (
    LoginForm,
    ProfileForm,
    RegistrationForm,
    TwoFactorForm,
    UserSettingsForm,
)
from apps.users.models import (
    EmailVerificationToken,
    Profile,
    TwoFactorCode,
    User,
)
from apps.users.services import (
    create_two_factor_code,
    login_user,
    register_user,
    update_profile,
    update_user_settings,
    verify_email_token,
    verify_two_factor_code,
)


class RegistrationFormTests(TestCase):

    def test_valid_registration_form(self):
        form = RegistrationForm(
            data={
                "username": "new_user",
                "email": "new@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "date_of_birth": "2000-01-01",
                "country": "Bulgaria",
            }
        )

        self.assertTrue(form.is_valid())

    def test_registration_form_rejects_existing_username(self):
        register_user(
            username="existing_user",
            email="existing@example.com",
            password="StrongPassword123!",
            country="Bulgaria",
        )

        form = RegistrationForm(
            data={
                "username": "existing_user",
                "email": "another@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "country": "Bulgaria",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_registration_form_rejects_existing_email(self):
        register_user(
            username="existing_email_user",
            email="existing@example.com",
            password="StrongPassword123!",
            country="Bulgaria",
        )

        form = RegistrationForm(
            data={
                "username": "another_user",
                "email": "existing@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "country": "Bulgaria",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_registration_form_rejects_different_passwords(self):
        form = RegistrationForm(
            data={
                "username": "password_user",
                "email": "password@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "DifferentPassword123!",
                "country": "Bulgaria",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertTrue(
            any(
                "Passwords do not match."
                in error
                for error in form.non_field_errors()
            )
        )


class EmailVerificationTests(TestCase):

    def test_registration_creates_verification_token(self):
        user, raw_token = register_user(
            username="registration_user",
            email="registration@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        verification_token = (
            EmailVerificationToken.objects
            .filter(user=user)
            .first()
        )

        self.assertIsNotNone(verification_token)
        self.assertIsNotNone(raw_token)
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(verification_token.expires_at)
        self.assertGreater(
            verification_token.expires_at,
            timezone.now(),
        )

    def test_verify_valid_token(self):
        user, raw_token = register_user(
            username="verification_user",
            email="verification@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        result = verify_email_token(raw_token)

        user.refresh_from_db()

        verification_token = (
            EmailVerificationToken.objects
            .filter(user=user)
            .first()
        )

        self.assertTrue(result)
        self.assertTrue(user.is_email_verified)
        self.assertIsNotNone(verification_token.used_at)

    def test_verify_invalid_token(self):
        user, raw_token = register_user(
            username="invalid_token_user",
            email="invalid@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        result = verify_email_token(
            "this-token-does-not-exist"
        )

        user.refresh_from_db()

        self.assertFalse(result)
        self.assertFalse(user.is_email_verified)

    def test_verify_expired_token(self):
        user, raw_token = register_user(
            username="expired_token_user",
            email="expired@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        verification_token = (
            EmailVerificationToken.objects
            .filter(user=user)
            .first()
        )

        verification_token.expires_at = (
            timezone.now() - timedelta(hours=1)
        )
        verification_token.save(
            update_fields=["expires_at"]
        )

        result = verify_email_token(raw_token)

        user.refresh_from_db()

        self.assertFalse(result)
        self.assertFalse(user.is_email_verified)
        self.assertIsNone(verification_token.used_at)

    def test_verify_token_can_only_be_used_once(self):
        user, raw_token = register_user(
            username="used_token_user",
            email="used@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        first_result = verify_email_token(raw_token)
        second_result = verify_email_token(raw_token)

        self.assertTrue(first_result)
        self.assertFalse(second_result)


class EmailVerificationViewTests(TestCase):

    def test_verify_email_view_with_valid_token(self):
        user, raw_token = register_user(
            username="view_valid_user",
            email="view_valid@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        response = self.client.get(
            reverse(
                "verify-email",
                kwargs={"token": raw_token},
            )
        )

        user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Email verified successfully!",
        )
        self.assertTrue(user.is_email_verified)

    def test_verify_email_view_with_invalid_token(self):
        response = self.client.get(
            reverse(
                "verify-email",
                kwargs={"token": "invalid-token"},
            )
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Email verification failed",
            status_code=400,
        )


class EmailSendingTests(TestCase):

    def test_verification_email_is_sent(self):
        user, raw_token = register_user(
            username="email_user",
            email="email@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        send_verification_email(
            user,
            raw_token,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.subject,
            "Verify your Budget Tracker email",
        )

        self.assertIn(
            user.email,
            email.to,
        )

        self.assertIn(
            raw_token,
            email.body,
        )

    def test_two_factor_email_is_sent(self):
        user, _ = register_user(
            username="twofa_email_user",
            email="twofa_email@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        raw_code = "583214"

        from apps.users.emails import send_two_factor_email

        send_two_factor_email(
            user,
            raw_code,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.subject,
            "Your Budget Tracker verification code",
        )

        self.assertIn(
            user.email,
            email.to,
        )

        self.assertIn(
            raw_code,
            email.body,
        )

    def test_two_factor_email_contains_html_version(self):
        user, _ = register_user(
            username="twofa_html_user",
            email="twofa_html@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        raw_code = "714205"

        from apps.users.emails import send_two_factor_email

        send_two_factor_email(
            user,
            raw_code,
        )

        email = mail.outbox[0]

        self.assertTrue(
            email.alternatives
        )

        html_message = email.alternatives[0][0]

        self.assertIn(
            raw_code,
            html_message,
        )

        self.assertIn(
            user.username,
            html_message,
        )

        self.assertIn(
            "This code expires in 10 minutes.",
            html_message,
        )

    def test_two_factor_email_contains_security_message(self):
        user, _ = register_user(
            username="twofa_security_user",
            email="twofa_security@example.com",
            password="TestPassword123!",
            country="Bulgaria",
        )

        raw_code = "926431"

        from apps.users.emails import send_two_factor_email

        send_two_factor_email(
            user,
            raw_code,
        )

        email = mail.outbox[0]

        html_message = email.alternatives[0][0]

        self.assertIn(
            "never share this verification code with anyone",
            html_message,
        )


class TwoFactorCodeTests(TestCase):

    def setUp(self):
        self.user, _ = register_user(
            username="twofa_user",
            email="twofa@example.com",
            password="StrongPassword123!",
            country="Bulgaria",
        )

    def test_create_two_factor_code(self):
        raw_code = create_two_factor_code(
            self.user
        )

        self.assertEqual(
            len(raw_code),
            6,
        )

        self.assertTrue(
            raw_code.isdigit()
        )

        two_factor_code = (
            TwoFactorCode.objects.get(
                user=self.user
            )
        )

        self.assertNotEqual(
            two_factor_code.code_hash,
            raw_code,
        )

        self.assertIsNotNone(
            two_factor_code.expires_at
        )

    def test_verify_correct_two_factor_code(self):
        raw_code = create_two_factor_code(
            self.user
        )

        result = verify_two_factor_code(
            self.user,
            raw_code,
        )

        self.assertTrue(result)

        two_factor_code = (
            TwoFactorCode.objects.get(
                user=self.user
            )
        )

        self.assertIsNotNone(
            two_factor_code.used_at
        )

    def test_verify_wrong_two_factor_code(self):
        create_two_factor_code(
            self.user
        )

        result = verify_two_factor_code(
            self.user,
            "000000",
        )

        self.assertFalse(result)

        two_factor_code = (
            TwoFactorCode.objects.get(
                user=self.user
            )
        )

        self.assertEqual(
            two_factor_code.attempts,
            1,
        )

    def test_two_factor_code_expires(self):
        raw_code = create_two_factor_code(
            self.user
        )

        two_factor_code = (
            TwoFactorCode.objects.get(
                user=self.user
            )
        )

        two_factor_code.expires_at = (
            timezone.now()
            - timedelta(minutes=1)
        )

        two_factor_code.save(
            update_fields=["expires_at"]
        )

        result = verify_two_factor_code(
            self.user,
            raw_code,
        )

        self.assertFalse(result)

    def test_two_factor_code_cannot_be_reused(self):
        raw_code = create_two_factor_code(
            self.user
        )

        first_result = verify_two_factor_code(
            self.user,
            raw_code,
        )

        second_result = verify_two_factor_code(
            self.user,
            raw_code,
        )

        self.assertTrue(first_result)
        self.assertFalse(second_result)

    def test_two_factor_code_blocks_after_five_failed_attempts(self):
        raw_code = create_two_factor_code(
            self.user
        )

        for _ in range(5):
            result = verify_two_factor_code(
                self.user,
                "000000",
            )

            self.assertFalse(result)

        two_factor_code = (
            TwoFactorCode.objects.get(
                user=self.user
            )
        )

        self.assertEqual(
            two_factor_code.attempts,
            5,
        )

        result = verify_two_factor_code(
            self.user,
            raw_code,
        )

        self.assertFalse(result)

    def test_latest_two_factor_code_is_used(self):
        first_code = create_two_factor_code(
            self.user
        )

        second_code = create_two_factor_code(
            self.user
        )

        first_result = verify_two_factor_code(
            self.user,
            first_code,
        )

        second_result = verify_two_factor_code(
            self.user,
            second_code,
        )

        self.assertFalse(first_result)
        self.assertTrue(second_result)


class LoginFormTests(TestCase):

    def test_valid_login_form(self):
        form = LoginForm(
            data={
                "username": "login_user",
                "password": "StrongPassword123!",
            }
        )

        self.assertTrue(form.is_valid())

    def test_login_form_requires_username(self):
        form = LoginForm(
            data={
                "password": "StrongPassword123!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "username",
            form.errors,
        )

    def test_login_form_requires_password(self):
        form = LoginForm(
            data={
                "username": "login_user",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "password",
            form.errors,
        )


class LoginServiceTests(TestCase):

    def create_verified_user(
        self,
        username="login_service_user",
        email="login_service@example.com",
    ):
        user, _ = register_user(
            username=username,
            email=email,
            password="StrongPassword123!",
            country="Bulgaria",
        )

        user.is_email_verified = True
        user.save(
            update_fields=["is_email_verified"]
        )

        return user

    def test_login_with_valid_credentials(self):
        self.create_verified_user()

        user = login_user(
            username="login_service_user",
            password="StrongPassword123!",
        )

        self.assertIsNotNone(user)
        self.assertEqual(
            user.username,
            "login_service_user",
        )

    def test_login_rejects_wrong_password(self):
        self.create_verified_user()

        user = login_user(
            username="login_service_user",
            password="WrongPassword123!",
        )

        self.assertIsNone(user)

    def test_login_rejects_nonexistent_user(self):
        user = login_user(
            username="does_not_exist",
            password="StrongPassword123!",
        )

        self.assertIsNone(user)

    def test_login_rejects_inactive_user(self):
        user = self.create_verified_user()

        user.is_active = False
        user.save(
            update_fields=["is_active"]
        )

        authenticated_user = login_user(
            username="login_service_user",
            password="StrongPassword123!",
        )

        self.assertIsNone(authenticated_user)

    def test_login_rejects_unverified_email(self):
        user, _ = register_user(
            username="unverified_login_user",
            email="unverified_login@example.com",
            password="StrongPassword123!",
            country="Bulgaria",
        )

        self.assertFalse(
            user.is_email_verified
        )

        authenticated_user = login_user(
            username="unverified_login_user",
            password="StrongPassword123!",
        )

        self.assertIsNone(authenticated_user)

    def test_login_returns_verified_user(self):
        user = self.create_verified_user(
            username="verified_login_user",
            email="verified_login@example.com",
        )

        authenticated_user = login_user(
            username="verified_login_user",
            password="StrongPassword123!",
        )

        self.assertEqual(
            authenticated_user.pk,
            user.pk,
        )
        self.assertTrue(
            authenticated_user.is_email_verified
        )


class LoginViewTests(TestCase):
    def setUp(self):
        self.user, _ = register_user(
            username="loginuser",
            email="login@example.com",
            password="StrongPassword123!",
            date_of_birth=None,
            country="Bulgaria",
            profile_picture=None,
        )

        self.user.is_email_verified = True
        self.user.save(update_fields=["is_email_verified"])

    def test_login_page_is_displayed(self):
        response = self.client.get(
            reverse("login")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "users/login.html",
        )

    def test_valid_login_redirects_to_2fa(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "loginuser",
                "password": "StrongPassword123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("verify-2fa"),
        )

        self.assertEqual(
            self.client.session["pending_2fa_user_id"],
            self.user.pk,
        )

    def test_valid_login_creates_two_factor_code(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "loginuser",
                "password": "StrongPassword123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("verify-2fa"),
        )

        self.assertEqual(
            self.user.two_factor_codes.count(),
            1,
        )

    def test_invalid_password_does_not_login(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "loginuser",
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "users/login.html",
        )

        self.assertNotIn(
            "pending_2fa_user_id",
            self.client.session,
        )

    def test_unverified_email_does_not_login(self):
        self.user.is_email_verified = False
        self.user.save(
            update_fields=["is_email_verified"]
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "loginuser",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "users/login.html",
        )

        self.assertNotIn(
            "pending_2fa_user_id",
            self.client.session,
        )

    def test_inactive_user_does_not_login(self):
        self.user.is_active = False
        self.user.save(
            update_fields=["is_active"]
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "loginuser",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "pending_2fa_user_id",
            self.client.session,
        )

    def test_login_without_2fa_authenticates_user_directly(self):
        self.user.two_fa_enabled = False
        self.user.save(
            update_fields=["two_fa_enabled"]
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "loginuser",
                "password": "StrongPassword123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
        )

        session = self.client.session

        self.assertEqual(
            int(session["_auth_user_id"]),
            self.user.pk,
        )


class TwoFactorFormTests(TestCase):
    def test_valid_code(self):
        form = TwoFactorForm(
            data={
                "code": "123456",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["code"],
            "123456",
        )

    def test_code_must_have_six_digits(self):
        form = TwoFactorForm(
            data={
                "code": "12345",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "code",
            form.errors,
        )

    def test_code_cannot_have_more_than_six_digits(self):
        form = TwoFactorForm(
            data={
                "code": "1234567",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "code",
            form.errors,
        )

    def test_code_must_contain_only_digits(self):
        form = TwoFactorForm(
            data={
                "code": "12AB56",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "code",
            form.errors,
        )

    def test_code_can_start_with_zero(self):
        form = TwoFactorForm(
            data={
                "code": "001234",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["code"],
            "001234",
        )


class VerifyTwoFactorViewTests(TestCase):
    def setUp(self):
        self.user, _ = register_user(
            username="twofauser",
            email="twofa@example.com",
            password="StrongPassword123!",
            date_of_birth=None,
            country="Bulgaria",
            profile_picture=None,
        )

        self.user.is_email_verified = True
        self.user.save(
            update_fields=["is_email_verified"]
        )

        self.raw_code = create_two_factor_code(
            self.user
        )

        session = self.client.session
        session["pending_2fa_user_id"] = self.user.pk
        session.save()

    def test_two_factor_page_is_displayed(self):
        response = self.client.get(
            reverse("verify-2fa")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "users/verify_2fa.html",
        )

    def test_missing_pending_user_redirects_to_login(self):
        session = self.client.session
        session.pop(
            "pending_2fa_user_id",
            None,
        )
        session.save()

        response = self.client.get(
            reverse("verify-2fa")
        )

        self.assertRedirects(
            response,
            reverse("login"),
        )

    def test_invalid_pending_user_redirects_to_login(self):
        session = self.client.session
        session["pending_2fa_user_id"] = 999999
        session.save()

        response = self.client.get(
            reverse("verify-2fa")
        )

        self.assertRedirects(
            response,
            reverse("login"),
        )

        self.assertNotIn(
            "pending_2fa_user_id",
            self.client.session,
        )

    def test_correct_code_authenticates_user(self):
        response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": self.raw_code,
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
        )

        session = self.client.session

        self.assertEqual(
            int(session["_auth_user_id"]),
            self.user.pk,
        )

    def test_correct_code_clears_pending_2fa_session(self):
        response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": self.raw_code,
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
        )

        self.assertNotIn(
            "pending_2fa_user_id",
            self.client.session,
        )

    def test_correct_code_marks_code_as_used(self):
        response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": self.raw_code,
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
        )

        two_factor_code = (
            self.user.two_factor_codes.first()
        )

        self.assertIsNotNone(
            two_factor_code.used_at
        )

    def test_invalid_code_does_not_authenticate_user(self):
        response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": "999999",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "users/verify_2fa.html",
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_invalid_code_increases_attempts(self):
        response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": "999999",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        two_factor_code = (
            self.user.two_factor_codes.first()
        )

        self.assertEqual(
            two_factor_code.attempts,
            1,
        )

    def test_expired_code_does_not_authenticate_user(self):
        two_factor_code = (
            self.user.two_factor_codes.first()
        )

        two_factor_code.expires_at = (
            timezone.now() - timedelta(minutes=1)
        )

        two_factor_code.save(
            update_fields=["expires_at"]
        )

        response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": self.raw_code,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_five_failed_attempts_do_not_authenticate_user(self):
        for _ in range(5):
            response = self.client.post(
                reverse("verify-2fa"),
                {
                    "code": "999999",
                },
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        two_factor_code = (
            self.user.two_factor_codes.first()
        )

        self.assertEqual(
            two_factor_code.attempts,
            5,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_successful_code_cannot_be_reused(self):
        first_response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": self.raw_code,
            },
        )

        self.assertRedirects(
            first_response,
            reverse("dashboard"),
        )

        self.client.logout()

        session = self.client.session
        session["pending_2fa_user_id"] = self.user.pk
        session.save()

        second_response = self.client.post(
            reverse("verify-2fa"),
            {
                "code": self.raw_code,
            },
        )

        self.assertEqual(
            second_response.status_code,
            200,
        )

        self.assertTemplateUsed(
            second_response,
            "users/verify_2fa.html",
        )


class ProfileAndSettingsFormTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.gbp = Currency.objects.get(code="GBP")

        self.user = User.objects.create_user(
            username="profile_user",
            email="profile@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        self.profile = Profile.objects.create(
            user=self.user,
            country="Bulgaria",
        )

    def test_profile_form_accepts_valid_data(self):
        form = ProfileForm(
            data={
                "date_of_birth": "2000-01-01",
                "country": "Bulgaria",
            },
            instance=self.profile,
        )

        self.assertTrue(form.is_valid())

    def test_profile_form_rejects_empty_country(self):
        form = ProfileForm(
            data={
                "date_of_birth": "2000-01-01",
                "country": "",
            },
            instance=self.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("country", form.errors)

    def test_profile_form_strips_country(self):
        form = ProfileForm(
            data={
                "date_of_birth": "2000-01-01",
                "country": "  Bulgaria  ",
            },
            instance=self.profile,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["country"],
            "Bulgaria",
        )

    def test_settings_form_shows_only_supported_currencies(self):
        form = UserSettingsForm(instance=self.user)

        currency_codes = list(
            form.fields["base_currency"]
            .queryset
            .values_list("code", flat=True)
        )

        self.assertEqual(
            currency_codes,
            ["EUR", "GBP", "USD"],
        )

    def test_settings_form_accepts_valid_data(self):
        form = UserSettingsForm(
            data={
                "base_currency": self.gbp.pk,
                "language": "en",
                "two_fa_enabled": True,
            },
            instance=self.user,
        )

        self.assertTrue(form.is_valid())

    def test_settings_form_updates_user_values(self):
        form = UserSettingsForm(
            data={
                "base_currency": self.gbp.pk,
                "language": "en",
                "two_fa_enabled": False,
            },
            instance=self.user,
        )

        self.assertTrue(form.is_valid())

        updated_user = form.save()

        self.assertEqual(
            updated_user.base_currency.code,
            "GBP",
        )
        self.assertEqual(
            updated_user.language,
            "en",
        )
        self.assertFalse(
            updated_user.two_fa_enabled,
        )


class ProfileAndSettingsServiceTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.gbp = Currency.objects.get(code="GBP")

        self.user = User.objects.create_user(
            username="service_user",
            email="service@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        self.profile = Profile.objects.create(
            user=self.user,
            country="Bulgaria",
        )

    def test_update_profile_updates_profile_data(self):
        updated_profile = update_profile(
            self.user,
            date_of_birth=date(2001, 5, 10),
            country="  Germany  ",
        )

        self.assertEqual(
            updated_profile.country,
            "Germany",
        )

        self.assertEqual(
            str(updated_profile.date_of_birth),
            "2001-05-10",
        )

    def test_update_profile_updates_profile_picture(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile(
            "profile.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )

        updated_profile = update_profile(
            self.user,
            profile_picture=image,
        )

        self.assertTrue(
            updated_profile.profile_picture.name.startswith(
                "profile_pictures/"
            )
        )

    def test_update_profile_does_not_change_omitted_values(self):
        self.profile.date_of_birth = date(2000, 1, 1)
        self.profile.save()

        updated_profile = update_profile(
            self.user,
            country="Bulgaria",
        )

        self.assertEqual(
            updated_profile.country,
            "Bulgaria",
        )

        self.assertEqual(
            str(updated_profile.date_of_birth),
            "2000-01-01",
        )

    def test_update_user_settings_updates_values(self):
        updated_user = update_user_settings(
            self.user,
            base_currency=self.gbp,
            language="en",
            two_fa_enabled=False,
        )

        self.assertEqual(
            updated_user.base_currency,
            self.gbp,
        )

        self.assertEqual(
            updated_user.language,
            "en",
        )

        self.assertFalse(
            updated_user.two_fa_enabled,
        )

    def test_update_user_settings_keeps_other_user_data(self):
        self.user.first_name = "Stefan"
        self.user.last_name = "Test"
        self.user.save()

        updated_user = update_user_settings(
            self.user,
            base_currency=self.gbp,
            language="en",
            two_fa_enabled=False,
        )

        self.assertEqual(
            updated_user.first_name,
            "Stefan",
        )

        self.assertEqual(
            updated_user.last_name,
            "Test",
        )


class ProfileViewTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.gbp = Currency.objects.get(code="GBP")

        self.user = User.objects.create_user(
            username="view_user",
            email="view@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        self.profile = Profile.objects.create(
            user=self.user,
            country="Bulgaria",
        )

    def test_profile_requires_login(self):
        response = self.client.get(
            reverse("profile")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("login"),
            response.url,
        )

    def test_authenticated_user_can_open_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("profile")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "users/profile.html",
        )

        self.assertContains(
            response,
            "Профил и настройки",
        )

    def test_profile_form_updates_profile(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            {
                "form_type": "profile",
                "date_of_birth": "1999-06-15",
                "country": "Germany",
            },
        )

        self.assertRedirects(
            response,
            reverse("profile"),
        )

        self.profile.refresh_from_db()

        self.assertEqual(
            self.profile.country,
            "Germany",
        )

        self.assertEqual(
            self.profile.date_of_birth,
            date(1999, 6, 15),
        )

    def test_settings_form_updates_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            {
                "form_type": "settings",
                "base_currency": self.gbp.pk,
                "language": "en",
                "two_fa_enabled": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("profile"),
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.base_currency,
            self.gbp,
        )

        self.assertEqual(
            self.user.language,
            "en",
        )

        self.assertTrue(
            self.user.two_fa_enabled,
        )

    def test_settings_form_can_disable_two_factor_authentication(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            {
                "form_type": "settings",
                "base_currency": self.eur.pk,
                "language": "bg",
            },
        )

        self.assertRedirects(
            response,
            reverse("profile"),
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.two_fa_enabled,
        )

    def test_profile_and_settings_are_independent(self):
        self.client.force_login(self.user)

        self.client.post(
            reverse("profile"),
            {
                "form_type": "profile",
                "date_of_birth": "2000-01-01",
                "country": "Bulgaria",
            },
        )

        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(
            self.profile.country,
            "Bulgaria",
        )

        self.assertEqual(
            self.user.base_currency,
            self.eur,
        )

        self.assertEqual(
            self.user.language,
            "bg",
        )

        self.assertTrue(
            self.user.two_fa_enabled,
        )
    
    def test_authenticated_pages_show_profile_link(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("profile")
        )

        self.assertContains(
            response,
            f'href="{reverse("profile")}"',
        )

        self.assertContains(
            response,
            self.user.username,
        )