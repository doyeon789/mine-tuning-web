from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

from .models import ChatMessage, ChatSession
from .views import _user_sessions


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
        self.assertEqual(session.title, f"새 채팅 {session.pk}")
        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))

    def test_create_session_reuses_existing_empty_session(self):
        empty_session = ChatSession.objects.create(owner=self.user, title="새 채팅")

        response = self.client.post(reverse("mine_chat:session_create"))

        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertRedirects(
            response,
            reverse("mine_chat:session_detail", args=[empty_session.pk]),
        )

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

    def test_sessions_order_by_latest_message_not_rename_time(self):
        older_session = ChatSession.objects.create(owner=self.user, title="Older")
        newer_session = ChatSession.objects.create(owner=self.user, title="Newer")
        now = timezone.now()
        older_message = ChatMessage.objects.create(
            session=older_session,
            role=ChatMessage.Role.USER,
            content="Older message",
        )
        newer_message = ChatMessage.objects.create(
            session=newer_session,
            role=ChatMessage.Role.USER,
            content="Newer message",
        )
        ChatMessage.objects.filter(pk=older_message.pk).update(created_at=now - timedelta(hours=1))
        ChatMessage.objects.filter(pk=newer_message.pk).update(created_at=now)

        self.client.post(
            reverse("mine_chat:session_update", args=[older_session.pk]),
            {"title": "Renamed older"},
        )

        sessions = list(_user_sessions(self.user))
        self.assertEqual(sessions[0], newer_session)
        self.assertEqual(sessions[1], older_session)

    def test_update_user_message_removes_later_messages_and_recreates_response(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")
        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content="Before",
        )
        old_assistant_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="Old answer",
        )
        later_user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content="Later question",
        )
        later_assistant_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="Later answer",
        )

        response = self.client.post(
            reverse("mine_chat:message_update", args=[user_message.pk]),
            {"content": "After"},
        )

        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        user_message.refresh_from_db()
        self.assertEqual(user_message.content, "After")
        self.assertFalse(ChatMessage.objects.filter(pk=old_assistant_message.pk).exists())
        self.assertFalse(ChatMessage.objects.filter(pk=later_user_message.pk).exists())
        self.assertFalse(ChatMessage.objects.filter(pk=later_assistant_message.pk).exists())
        self.assertEqual(session.messages.filter(role=ChatMessage.Role.USER).count(), 1)
        self.assertEqual(session.messages.filter(role=ChatMessage.Role.ASSISTANT).count(), 1)

    def test_assistant_message_cannot_be_updated(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")
        assistant_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="Answer",
        )

        response = self.client.post(
            reverse("mine_chat:message_update", args=[assistant_message.pk]),
            {"content": "Edited"},
        )

        self.assertEqual(response.status_code, 404)
        assistant_message.refresh_from_db()
        self.assertEqual(assistant_message.content, "Answer")
