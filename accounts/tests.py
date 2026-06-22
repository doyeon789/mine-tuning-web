from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AccountViewsTests(TestCase):
    def test_signup_creates_and_logs_in_user(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "newuser",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("mine_chat:index"))
        self.assertTrue(get_user_model().objects.filter(username="newuser").exists())

    def test_signup_duplicate_username_uses_korean_label(self):
        get_user_model().objects.create_user(
            username="tester",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "tester",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertContains(response, "아이디")
        self.assertContains(response, "이미 사용 중인 아이디입니다.")
        self.assertNotContains(response, "A user with that username already exists.")

    def test_login_and_logout(self):
        get_user_model().objects.create_user(
            username="tester",
            password="StrongPass123!",
        )

        login_response = self.client.post(
            reverse("accounts:login"),
            {"username": "tester", "password": "StrongPass123!"},
        )
        self.assertRedirects(login_response, reverse("mine_chat:index"))

        logout_response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(logout_response, reverse("accounts:login"))

    def test_delete_account_removes_current_user(self):
        get_user_model().objects.create_user(
            username="tester",
            password="StrongPass123!",
        )
        self.client.login(username="tester", password="StrongPass123!")

        response = self.client.post(reverse("accounts:delete"))

        self.assertRedirects(response, reverse("accounts:signup"))
        self.assertFalse(get_user_model().objects.filter(username="tester").exists())
