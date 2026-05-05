from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ChatMessageForm, ChatSessionForm
from .models import ChatMessage, ChatSession


def _chat_context(active_session=None, message_form=None, session_form=None):
    return {
        "sessions": ChatSession.objects.all(),
        "active_session": active_session,
        "message_form": message_form or ChatMessageForm(),
        "session_form": session_form or ChatSessionForm(instance=active_session),
    }


def index(request):
    first_session = ChatSession.objects.first()
    if first_session:
        return redirect("mine_chat:session_detail", pk=first_session.pk)
    return render(request, "mine_chat/index.html", _chat_context())


def session_detail(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    return render(request, "mine_chat/index.html", _chat_context(active_session=session))


@require_POST
def session_create(request):
    session = ChatSession.objects.create()
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
def session_update(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    form = ChatSessionForm(request.POST, instance=session)
    if form.is_valid():
        form.save()
    return redirect("mine_chat:session_detail", pk=session.pk)


@require_POST
def session_delete(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    session.delete()
    return redirect("mine_chat:index")


@require_POST
def message_create(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    form = ChatMessageForm(request.POST)
    if form.is_valid():
        message = form.save(commit=False)
        message.session = session
        message.role = ChatMessage.Role.USER
        message.save()
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="아직 LLM API가 연결되지 않았습니다. 나중에 파인튜닝 모델 응답으로 교체하면 됩니다.",
        )
    return redirect(reverse("mine_chat:session_detail", kwargs={"pk": session.pk}))


@require_POST
def message_delete(request, pk):
    message = get_object_or_404(ChatMessage, pk=pk)
    session_pk = message.session_id
    message.delete()
    return redirect("mine_chat:session_detail", pk=session_pk)
