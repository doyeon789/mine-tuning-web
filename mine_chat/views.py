from django.contrib.auth.decorators import login_required
from django.db.models import DateTimeField, Max
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
import logging
import requests
import os
import re

from .forms import ChatMessageForm, ChatSessionForm
from .models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

NGROK_URL = os.environ.get("NGROK_URL", "https://eligibly-shove-cartload.ngrok-free.dev")
TITLE_API_URL = os.environ.get(
    "TITLE_API_URL",
    "https://title-api-server.onrender.com/api/titles/",
)
TITLE_API_TIMEOUT_SECONDS = float(os.environ.get("TITLE_API_TIMEOUT_SECONDS", "60"))
TITLE_API_MAX_ATTEMPTS = 2
SESSION_TITLE_MAX_LENGTH = 32


def _user_sessions(user):
    return (
        ChatSession.objects.filter(owner=user)
        .annotate(
            last_activity_at=Coalesce(
                Max("messages__created_at"),
                "created_at",
                output_field=DateTimeField(),
            )
        )
        .order_by("-is_pinned", "-last_activity_at", "-created_at")
    )


def _chat_context(user, active_session=None, message_form=None, session_form=None):
    sessions = list(_user_sessions(user))
    return {
        "sessions": sessions,
        "pinned_sessions": [session for session in sessions if session.is_pinned],
        "regular_sessions": [session for session in sessions if not session.is_pinned],
        "active_session": active_session,
        "message_form": message_form or ChatMessageForm(),
        "session_form": session_form or ChatSessionForm(instance=active_session),
    }


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _request_active_session(request, fallback_session=None):
    active_session_id = request.headers.get("x-active-session")
    if not active_session_id:
        return fallback_session

    try:
        return ChatSession.objects.get(pk=active_session_id, owner=request.user)
    except (ChatSession.DoesNotExist, ValueError):
        return fallback_session


def _chat_app_response(request, active_session=None):
    context = _chat_context(request.user, active_session=active_session)
    return JsonResponse(
        {
            "app_html": render_to_string(
                "mine_chat/_app_shell.html",
                context,
                request=request,
            )
        }
    )


def _call_rag_api(question: str) -> str:
    try:
        resp = requests.post(
            f"{NGROK_URL}/chat",
            json={"question": question},
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=60,
        )
        data = resp.json()
        
        answer = (
            data.get("validation", {}).get("corrected_answer")
            or "답변을 가져오지 못했습니다."
        )
        return answer
    except Exception as e:
        return f"API 연결 오류: {str(e)}"
    

def _normalize_generated_title(title):
    if not isinstance(title, str):
        return ""

    title = " ".join(title.split()).strip()
    title = title.strip("\"'`“”‘’[](){}")
    title = re.sub(r"[?!.,。！？]+$", "", title).strip()
    return title[:SESSION_TITLE_MAX_LENGTH].rstrip()


def _call_title_api(question, answer):
    last_error = None

    for attempt in range(1, TITLE_API_MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                TITLE_API_URL,
                json={
                    "question": question,
                    "answer": answer,
                },
                timeout=TITLE_API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                return ""
            return _normalize_generated_title(data.get("title"))
        except (requests.RequestException, ValueError, TypeError) as error:
            last_error = error
            logger.warning(
                "Title API request failed (attempt %s/%s): %s",
                attempt,
                TITLE_API_MAX_ATTEMPTS,
                error,
            )

    if last_error:
        raise last_error
    return ""


def _create_assistant_response(session, update_title=False):
    last_user_message = session.messages.filter(
        role=ChatMessage.Role.USER
    ).last()

    if last_user_message:
        answer = _call_rag_api(last_user_message.content)
    else:
        answer = "질문을 찾을 수 없습니다."

    assistant_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=answer,
    )

    if update_title and last_user_message:
        try:
            generated_title = _call_title_api(
                last_user_message.content,
                answer,
            )
        except (requests.RequestException, ValueError, TypeError):
            generated_title = ""

        if generated_title:
            session.title = generated_title
            session.save(update_fields=["title"])

    return assistant_message


def _delete_messages_after(user_message):
    ChatMessage.objects.filter(
        session=user_message.session,
        pk__gt=user_message.pk,
    ).delete()


def _delete_messages_from(user_message):
    ChatMessage.objects.filter(
        session=user_message.session,
        pk__gte=user_message.pk,
    ).delete()


def _make_session_title(content):
    title = " ".join(content.split())
    if len(title) <= SESSION_TITLE_MAX_LENGTH:
        return title
    return title[: SESSION_TITLE_MAX_LENGTH - 3].rstrip() + "..."


@login_required
def index(request):
    if request.GET.get("new") == "1":
        return render(request, "mine_chat/index.html", _chat_context(request.user))

    first_session = _user_sessions(request.user).first()
    if first_session:
        return redirect("mine_chat:session_detail", pk=first_session.pk)
    return render(request, "mine_chat/index.html", _chat_context(request.user))


@login_required
def session_detail(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    return render(request, "mine_chat/index.html", _chat_context(request.user, active_session=session))


@require_POST
@login_required
def session_create(request):
    form = ChatMessageForm(request.POST)
    if "content" not in request.POST or not form.is_valid():
        return redirect(f"{reverse('mine_chat:index')}?new=1")

    message = form.save(commit=False)
    session = ChatSession.objects.create(
        owner=request.user,
        title=_make_session_title(message.content),
    )
    message.session = session
    message.role = ChatMessage.Role.USER
    message.save()
    _create_assistant_response(session, update_title=True)

    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def session_update(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    form = ChatSessionForm(request.POST, instance=session)
    if form.is_valid():
        session = form.save()
    if _is_ajax(request):
        active_session = _request_active_session(request, session)
        if active_session and active_session.pk == session.pk:
            active_session = session
        return _chat_app_response(request, active_session=active_session)
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def session_delete(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    active_session = _request_active_session(request)
    deleting_active_session = active_session and active_session.pk == session.pk
    session.delete()
    if _is_ajax(request):
        if deleting_active_session:
            return JsonResponse({"redirect_url": reverse("mine_chat:index")})
        return _chat_app_response(request, active_session=active_session)
    return redirect("mine_chat:index")


@require_POST
@login_required
def session_pin(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    session.is_pinned = not session.is_pinned
    session.save(update_fields=["is_pinned"])
    if _is_ajax(request):
        return _chat_app_response(
            request,
            active_session=_request_active_session(request, session),
        )
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def message_create(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    form = ChatMessageForm(request.POST)
    if form.is_valid():
        message = form.save(commit=False)
        message.session = session
        message.role = ChatMessage.Role.USER
        message.save()
        _create_assistant_response(session)
    return redirect(reverse("mine_chat:session_detail", kwargs={"pk": session.pk}))


@require_POST
@login_required
def message_update(request, pk):
    message = get_object_or_404(
        ChatMessage,
        pk=pk,
        session__owner=request.user,
        role=ChatMessage.Role.USER,
    )
    form = ChatMessageForm(request.POST, instance=message)
    if form.is_valid():
        form.save()
        _delete_messages_after(message)
        _create_assistant_response(message.session)
    return redirect("mine_chat:session_detail", pk=message.session_id)


@require_POST
@login_required
def message_delete(request, pk):
    message = get_object_or_404(
        ChatMessage,
        pk=pk,
        session__owner=request.user,
        role=ChatMessage.Role.USER,
    )
    session = message.session
    first_user_message = session.messages.filter(
        role=ChatMessage.Role.USER,
    ).first()

    if first_user_message and first_user_message.pk == message.pk:
        session.delete()
        return redirect("mine_chat:index")

    session_id = message.session_id
    _delete_messages_from(message)
    return redirect("mine_chat:session_detail", pk=session_id)
