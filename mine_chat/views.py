from django.contrib.auth.decorators import login_required
from django.db.models import DateTimeField, Max
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
import requests
import os

from .forms import ChatMessageForm, ChatSessionForm
from .models import ChatMessage, ChatSession

NGROK_URL = os.environ.get("NGROK_URL", "https://eligibly-shove-cartload.ngrok-free.dev")
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


def _chat_app_response(request, active_session=None, status=200):
    context = _chat_context(request.user, active_session=active_session)
    return JsonResponse(
        {
            "app_html": render_to_string(
                "mine_chat/_app_shell.html",
                context,
                request=request,
            ),
            "url": (
                reverse("mine_chat:session_detail", args=[active_session.pk])
                if active_session
                else f"{reverse('mine_chat:index')}?new=1"
            ),
        },
        status=status,
    )


def _active_session_from_request(request):
    active_session_id = request.headers.get("x-active-session")
    if not active_session_id:
        return None

    try:
        return ChatSession.objects.get(pk=active_session_id, owner=request.user)
    except (ChatSession.DoesNotExist, ValueError):
        return None


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
    

def _create_assistant_response(session):
    last_user_message = session.messages.filter(
        role=ChatMessage.Role.USER
    ).last()

    if last_user_message:
        answer = _call_rag_api(last_user_message.content)
    else:
        answer = "질문을 찾을 수 없습니다."

    return ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=answer,
    )


def _delete_messages_after(user_message):
    ChatMessage.objects.filter(
        session=user_message.session,
        pk__gt=user_message.pk,
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
    _create_assistant_response(session)

    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def session_update(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    form = ChatSessionForm(request.POST, instance=session)
    if form.is_valid():
        session = form.save()
        if _is_ajax(request):
            return _chat_app_response(request, active_session=session)
    elif _is_ajax(request):
        return _chat_app_response(request, active_session=session, status=400)
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def session_delete(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    active_session = _active_session_from_request(request)
    session.delete()
    if _is_ajax(request):
        next_session = (
            active_session
            if active_session and active_session.pk != session.pk
            else _user_sessions(request.user).first()
        )
        return _chat_app_response(request, active_session=next_session)
    return redirect("mine_chat:index")


@require_POST
@login_required
def session_pin(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    session.is_pinned = not session.is_pinned
    session.save(update_fields=["is_pinned"])
    if _is_ajax(request):
        return _chat_app_response(request, active_session=session)
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
