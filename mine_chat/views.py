from django.contrib.auth.decorators import login_required
from django.db.models import DateTimeField, Max
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
import requests
import os
import re

from .forms import ChatMessageForm, ChatSessionForm
from .models import ChatMessage, ChatSession

NGROK_URL = os.environ.get("NGROK_URL", "https://eligibly-shove-cartload.ngrok-free.dev")
TITLE_API_URL = os.environ.get(
    "TITLE_API_URL",
    "http://127.0.0.1:8100/api/titles/",
)
TITLE_API_TIMEOUT_SECONDS = float(os.environ.get("TITLE_API_TIMEOUT_SECONDS", "30"))
SESSION_TITLE_MAX_LENGTH = 40
DEFAULT_SESSION_TITLE = "새 채팅"

TITLE_QUESTION_PATTERNS = (
    (r"^(.+?)\s+어떻게\s+캐(?:요|나요|지|야)?$", r"\1 캐는 법"),
    (r"^(.+?)\s+어떻게\s+가(?:요|나요|지|야)?$", r"\1 가는 법"),
    (r"^(.+?)\s+어떻게\s+만들(?:어|어요|지|까)?$", r"\1 만드는 법"),
    (r"^(.+?)\s+어떻게\s+얻(?:어|어요|지|지요|나요)?$", r"\1 얻는 법"),
    (r"^(.+?)\s+어떻게\s+찾(?:아|아요|지|나요)?$", r"\1 찾는 법"),
    (r"^(.+?)\s+어떻게\s+잡(?:아|아요|지|나요)?$", r"\1 잡는 법"),
    (r"^(.+?)\s+어떻게\s+쓰(?:지|나요|는 거야)?$", r"\1 쓰는 법"),
    (r"^(.+?)\s+어떻게\s+해(?:요|야|야 해|야 돼|야 하나요)?$", r"\1 하는 법"),
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


def _answer_for_title(answer):
    if not isinstance(answer, str):
        return ""

    cleaned = " ".join(answer.split()).strip()
    lowered = cleaned.casefold()
    if not cleaned:
        return ""
    if lowered.startswith("api "):
        return ""
    if any(
        marker in lowered
        for marker in (
            "connection error",
            "connection failed",
            "failed to connect",
            "request failed",
            "service unavailable",
            "unable to fetch",
        )
    ):
        return ""
    return cleaned


def _call_title_api(question, answer):
    response = requests.post(
        TITLE_API_URL,
        json={
            "question": question,
            "answer": _answer_for_title(answer),
        },
        timeout=TITLE_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        return ""
    return _normalize_generated_title(data.get("title"))


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
        fallback_title = _make_session_title(last_user_message.content)
        try:
            generated_title = _call_title_api(
                last_user_message.content,
                answer,
            )
        except (requests.RequestException, ValueError, TypeError):
            generated_title = ""

        session.title = generated_title or fallback_title
        session.save(update_fields=["title"])

    return assistant_message


def _delete_messages_after(user_message):
    ChatMessage.objects.filter(
        session=user_message.session,
        pk__gt=user_message.pk,
    ).delete()


def _make_session_title(content):
    title = " ".join(content.split()).strip()
    title = re.sub(r"[?!.,。！？]+", "", title).strip()

    recipe_match = re.fullmatch(
        r"what(?:'s|\s+is)\s+the\s+(?:crafting\s+)?recipe\s+(?:of|for)\s+"
        r"(?:(a|an|the)\s+)?(.+)",
        title,
        flags=re.IGNORECASE,
    )
    if recipe_match:
        article, subject = recipe_match.groups()
        subject = subject.strip().title()
        subject_with_article = f"{article.casefold()} {subject}" if article else subject
        title = f"How to Make {subject_with_article}"

    intent_match = re.fullmatch(
        r"(?:how\s+(?:do|can|should)\s+i|how\s+to)\s+"
        r"(craft|make|build|get|obtain|find|locate|reach|defeat|beat|use)\s+"
        r"(?:(a|an|the)\s+)?(.+)",
        title,
        flags=re.IGNORECASE,
    )
    if intent_match and not recipe_match:
        action, article, subject = intent_match.groups()
        subject = subject.strip().title()
        subject_with_article = f"{article.casefold()} {subject}" if article else subject
        action = action.casefold()
        if action in {"craft", "make", "build"}:
            title = f"How to Craft {subject_with_article}"
        elif action in {"get", "obtain"}:
            title = f"How to Get {subject_with_article}"
        elif action in {"find", "locate", "reach"}:
            title = f"How to Find {subject_with_article}"
        elif action in {"defeat", "beat"}:
            title = f"How to Defeat {subject_with_article}"
        else:
            title = f"How to Use {subject_with_article}"

    elif not recipe_match:
        generic_how_match = re.fullmatch(
            r"(?:how\s+(?:do|can|should)\s+i|how\s+to)\s+(.+)",
            title,
            flags=re.IGNORECASE,
        )
        if generic_how_match:
            action_phrase = generic_how_match.group(1).strip().title()
            title = f"How to {action_phrase}"

    if title.casefold() in {"hi", "hello", "ㅎㅇ", "안녕", "안녕하세요"}:
        return DEFAULT_SESSION_TITLE

    for pattern, replacement in TITLE_QUESTION_PATTERNS:
        if re.fullmatch(pattern, title):
            title = re.sub(pattern, replacement, title)
            break

    title = re.sub(
        r"\s*(?:(?:자세히\s*)?알려\s*줘|(?:자세히\s*)?알려\s*주세요|"
        r"(?:자세히\s*)?설명해\s*줘|(?:자세히\s*)?설명해\s*주세요|"
        r"(?:자세히\s*)?가르쳐\s*줘|(?:자세히\s*)?가르쳐\s*주세요)$",
        "",
        title,
    ).strip()
    title = re.sub(
        r"^(?:마인크래프트에서\s+)?(.+?)(?:을|를)\s+"
        r"(?:(?:가장\s+)?빠르게\s+)?(.+?는)\s+방법(?:을)?$",
        r"\1 \2 방법",
        title,
    )
    title = re.sub(r"는\s*법", "는 법", title)

    if not title:
        return DEFAULT_SESSION_TITLE
    if len(title) <= SESSION_TITLE_MAX_LENGTH:
        return title

    shortened_title = title[:SESSION_TITLE_MAX_LENGTH].rstrip()
    if " " in shortened_title:
        shortened_title = shortened_title.rsplit(" ", 1)[0]
    return shortened_title or title[:SESSION_TITLE_MAX_LENGTH].rstrip()


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
        title=DEFAULT_SESSION_TITLE,
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
def session_pin(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, owner=request.user)
    session.is_pinned = not session.is_pinned
    session.save(update_fields=["is_pinned"])
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
