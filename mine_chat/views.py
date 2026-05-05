from django.contrib.auth.decorators import login_required
from django.db.models import Count, DateTimeField, Max
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ChatMessageForm, ChatSessionForm
from .models import ChatMessage, ChatSession

ASSISTANT_PLACEHOLDER = (
    "아직 LLM API가 연결되지 않았습니다. 나중에 파인튜닝 모델 응답으로 교체하면 됩니다."
)


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
        .order_by("-last_activity_at", "-created_at")
    )


def _chat_context(user, active_session=None, message_form=None, session_form=None):
    return {
        "sessions": _user_sessions(user),
        "active_session": active_session,
        "message_form": message_form or ChatMessageForm(),
        "session_form": session_form or ChatSessionForm(instance=active_session),
    }


def _create_assistant_response(session):
    return ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=ASSISTANT_PLACEHOLDER,
    )


def _delete_messages_after(user_message):
    ChatMessage.objects.filter(
        session=user_message.session,
        pk__gt=user_message.pk,
    ).delete()


@login_required
def index(request):
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
    session = (
        _user_sessions(request.user)
        .annotate(message_count=Count("messages"))
        .filter(message_count=0)
        .first()
    )
    if session is None:
        session = ChatSession.objects.create(owner=request.user)
        session.title = f"새 채팅 {session.pk}"
        session.save(update_fields=["title"])
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def session_update(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    form = ChatSessionForm(request.POST, instance=session)
    if form.is_valid():
        form.save()
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
@login_required
def session_delete(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    session.delete()
    return redirect("mine_chat:index")


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
