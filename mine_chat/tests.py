from datetime import timedelta
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone

from .models import ChatMessage, ChatSession
from .views import (
    SESSION_TITLE_MAX_LENGTH,
    _call_title_api,
    _make_session_title,
    _user_sessions,
)


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
        self.assertContains(response, escape(response.context["auth_splash"]))
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

    @patch("mine_chat.views._call_rag_api", return_value="Answer")
    def test_ajax_message_create_returns_updated_chat_app(self, _call_rag_api):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")

        response = self.client.post(
            reverse("mine_chat:message_create", args=[session.pk]),
            {"content": "Hello"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["url"],
            reverse("mine_chat:session_detail", args=[session.pk]),
        )
        self.assertIn("data-chat-app", response.json()["app_html"])
        self.assertIn("Answer", response.json()["app_html"])

    def test_existing_chat_renders_loading_state_hooks(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")

        response = self.client.get(
            reverse("mine_chat:session_detail", args=[session.pk])
        )

        self.assertContains(response, "data-chat-submit-form")
        self.assertContains(response, "data-pending-response-host")
        self.assertContains(response, "send-button-loader")

    @patch("mine_chat.views._call_title_api")
    @patch("mine_chat.views._call_rag_api")
    def test_create_session_with_content_starts_chat(self, call_rag_api, call_title_api):
        call_rag_api.return_value = "Generated answer"
        call_title_api.return_value = "Generated title"

        response = self.client.post(
            reverse("mine_chat:session_create"),
            {"content": "First message"},
        )

        session = ChatSession.objects.get()
        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        self.assertEqual(session.owner, self.user)
        self.assertEqual(session.title, "Generated title")
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(session.messages.first().role, ChatMessage.Role.USER)
        self.assertEqual(session.messages.first().content, "First message")
        call_title_api.assert_called_once_with("First message", "Generated answer")

    @patch("mine_chat.views._call_title_api")
    @patch("mine_chat.views._call_rag_api")
    def test_session_title_is_received_from_title_server(
        self,
        call_rag_api,
        call_title_api,
    ):
        call_rag_api.return_value = "다이아몬드는 Y -59 부근에서 찾기 좋습니다."
        call_title_api.return_value = "다이아몬드 채굴법"

        response = self.client.post(
            reverse("mine_chat:session_create"),
            {"content": "  다이아 어떻게 캐?  "},
        )

        session = ChatSession.objects.get()
        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        self.assertEqual(session.title, "다이아몬드 채굴법")

    @patch("mine_chat.views._call_title_api")
    @patch("mine_chat.views._call_rag_api")
    def test_session_title_uses_fallback_when_title_server_fails(
        self,
        call_rag_api,
        call_title_api,
    ):
        call_rag_api.return_value = "Generated answer"
        call_title_api.side_effect = requests.RequestException("unavailable")

        self.client.post(
            reverse("mine_chat:session_create"),
            {"content": "다이아 어떻게 캐?"},
        )

        session = ChatSession.objects.get()
        self.assertEqual(session.title, "다이아 캐는 법")

    @patch("mine_chat.views._call_title_api")
    @patch("mine_chat.views._call_rag_api")
    def test_later_messages_do_not_change_session_title(
        self,
        call_rag_api,
        call_title_api,
    ):
        call_rag_api.return_value = "Generated answer"
        session = ChatSession.objects.create(
            owner=self.user,
            title="사용자 지정 제목",
        )

        self.client.post(
            reverse("mine_chat:message_create", args=[session.pk]),
            {"content": "다음 질문"},
        )

        session.refresh_from_db()
        self.assertEqual(session.title, "사용자 지정 제목")
        call_title_api.assert_not_called()

    def test_session_title_is_truncated_to_model_limit(self):
        long_question = "가" * 140

        title = _make_session_title(long_question)

        self.assertEqual(len(title), SESSION_TITLE_MAX_LENGTH)
        self.assertNotIn("...", title)

    def test_session_title_removes_request_ending_and_punctuation(self):
        title = _make_session_title("엔더 드래곤 공략 알려주세요!")

        self.assertEqual(title, "엔더 드래곤 공략")

    def test_greeting_uses_default_session_title(self):
        self.assertEqual(_make_session_title("ㅎㅇ"), "새 채팅")

    def test_english_crafting_question_keeps_subject(self):
        self.assertEqual(
            _make_session_title("How do I craft an iron pickaxe?"),
            "How to Craft an Iron Pickaxe",
        )

    def test_unlisted_english_how_question_is_rewritten(self):
        self.assertEqual(
            _make_session_title("How do I mine diamonds?"),
            "How to Mine Diamonds",
        )

    def test_long_how_to_question_keeps_core_topic(self):
        title = _make_session_title(
            "마인크래프트에서 다이아몬드를 가장 빠르게 찾는 방법을 자세히 설명해주세요"
        )

        self.assertEqual(title, "다이아몬드 찾는 방법")

    @patch("mine_chat.views.requests.post")
    def test_title_api_sends_question_and_answer(self, post):
        post.return_value.json.return_value = {
            "title": '"다이아몬드 채굴법!"',
        }

        title = _call_title_api("다이아 어떻게 캐?", "Y -59를 탐색하세요.")

        self.assertEqual(title, "다이아몬드 채굴법")
        post.assert_called_once()
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "question": "다이아 어떻게 캐?",
                "answer": "Y -59를 탐색하세요.",
            },
        )

    @patch("mine_chat.views.requests.post")
    def test_title_api_ignores_connection_error_answer(self, post):
        post.return_value.json.return_value = {"title": "Beacon Crafting"}

        title = _call_title_api(
            "How do I craft a beacon?",
            "API connection error: timed out",
        )

        self.assertEqual(title, "Beacon Crafting")
        post.assert_called_once()
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "question": "How do I craft a beacon?",
                "answer": "",
            },
        )

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

    def test_pinned_sessions_are_ordered_before_recent_sessions(self):
        pinned_session = ChatSession.objects.create(
            owner=self.user,
            title="Pinned",
            is_pinned=True,
        )
        recent_session = ChatSession.objects.create(owner=self.user, title="Recent")
        now = timezone.now()
        pinned_message = ChatMessage.objects.create(
            session=pinned_session,
            role=ChatMessage.Role.USER,
            content="Pinned message",
        )
        recent_message = ChatMessage.objects.create(
            session=recent_session,
            role=ChatMessage.Role.USER,
            content="Recent message",
        )
        ChatMessage.objects.filter(pk=pinned_message.pk).update(created_at=now - timedelta(hours=1))
        ChatMessage.objects.filter(pk=recent_message.pk).update(created_at=now)

        sessions = list(_user_sessions(self.user))

        self.assertEqual(sessions[0], pinned_session)
        self.assertEqual(sessions[1], recent_session)

    def test_session_pin_toggles_pinned_state(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")

        response = self.client.post(reverse("mine_chat:session_pin", args=[session.pk]))

        self.assertRedirects(response, reverse("mine_chat:session_detail", args=[session.pk]))
        session.refresh_from_db()
        self.assertTrue(session.is_pinned)

        self.client.post(reverse("mine_chat:session_pin", args=[session.pk]))

        session.refresh_from_db()
        self.assertFalse(session.is_pinned)

    def test_ajax_session_update_returns_chat_app_html(self):
        session = ChatSession.objects.create(owner=self.user, title="Before")

        response = self.client.post(
            reverse("mine_chat:session_update", args=[session.pk]),
            {"title": "After"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('data-chat-app data-active-session-id="', data["app_html"])
        self.assertIn("After", data["app_html"])
        self.assertEqual(
            data["url"],
            reverse("mine_chat:session_detail", args=[session.pk]),
        )
        session.refresh_from_db()
        self.assertEqual(session.title, "After")

    def test_ajax_session_pin_returns_reordered_chat_app_html(self):
        session = ChatSession.objects.create(owner=self.user, title="Test chat")

        response = self.client.post(
            reverse("mine_chat:session_pin", args=[session.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("즐겨찾기 해제", data["app_html"])
        self.assertIn("pinned-history", data["app_html"])
        session.refresh_from_db()
        self.assertTrue(session.is_pinned)

    def test_ajax_session_delete_preserves_current_active_session(self):
        active_session = ChatSession.objects.create(owner=self.user, title="Active")
        other_session = ChatSession.objects.create(owner=self.user, title="Other")

        response = self.client.post(
            reverse("mine_chat:session_delete", args=[other_session.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_ACTIVE_SESSION=str(active_session.pk),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Active", data["app_html"])
        self.assertNotIn("Other", data["app_html"])
        self.assertEqual(
            data["url"],
            reverse("mine_chat:session_detail", args=[active_session.pk]),
        )
        self.assertFalse(ChatSession.objects.filter(pk=other_session.pk).exists())

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
