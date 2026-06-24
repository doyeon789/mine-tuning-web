from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import ChatMessage, ChatSession
from .views import SESSION_TITLE_MAX_LENGTH, _make_session_title, _user_sessions


class ChatViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="StrongPass123!",
        )
        self.client.login(username="tester", password="StrongPass123!")

    def test_new_chat_page_does_not_create_session(self):
        ChatSession.objects.create(owner=self.user, title="Existing")

        response = self.client.get(reverse("mine_chat:index"), {"new": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Where should we begin?")
        self.assertContains(response, "data-chat-submit-form")
        self.assertContains(response, "data-pending-response-host")
        self.assertContains(response, "data-first-chat")
        self.assertContains(response, "data-example-questions")
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertNotContains(response, '<div class="chat-topbar">', html=False)

    def test_empty_session_create_redirects_to_new_chat_without_creating_session(self):
        response = self.client.post(reverse("mine_chat:session_create"))

        self.assertEqual(ChatSession.objects.count(), 0)
        self.assertRedirects(response, f"{reverse('mine_chat:index')}?new=1")

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

    def test_existing_chat_renders_loading_state_hooks(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")

        response = self.client.get(
            reverse("mine_chat:session_detail", args=[session.pk])
        )

        self.assertContains(response, "data-chat-submit-form")
        self.assertContains(response, "data-pending-response-host")
        self.assertContains(response, "send-button-loader")

    def test_create_session_with_content_starts_chat(self):
        response = self.client.post(
            reverse("mine_chat:session_create"),
            {"content": "First message"},
        )

        session = ChatSession.objects.get()
        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        self.assertEqual(session.owner, self.user)
        self.assertEqual(session.title, "First message")
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(session.messages.first().role, ChatMessage.Role.USER)
        self.assertEqual(session.messages.first().content, "First message")

    def test_session_title_is_based_on_first_question(self):
        response = self.client.post(
            reverse("mine_chat:session_create"),
            {"content": "  다이아   캐는법\n알려줘  "},
        )

        session = ChatSession.objects.get()
        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        self.assertEqual(session.title, "다이아 캐는법 알려줘")

    def test_session_title_is_truncated_to_model_limit(self):
        long_question = "가" * 140

        title = _make_session_title(long_question)

        self.assertEqual(len(title), SESSION_TITLE_MAX_LENGTH)
        self.assertTrue(title.endswith("..."))

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
