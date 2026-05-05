from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ChatMessage, ChatSession


class ChatViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="StrongPass123!",
        )
        self.client.login(username="tester", password="StrongPass123!")

    def test_create_session_redirects_to_detail(self):
        response = self.client.post(reverse("mine_chat:session_create"))

        session = ChatSession.objects.get()
        self.assertEqual(session.owner, self.user)
        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))

    def test_create_message_adds_user_and_placeholder_assistant_message(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")

        response = self.client.post(
            reverse("mine_chat:message_create", args=[session.pk]),
            {"content": "Hello"},
        )

        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(session.messages.first().role, ChatMessage.Role.USER)
        self.assertEqual(session.messages.first().content, "Hello")
