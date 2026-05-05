from django import forms

from .models import ChatMessage, ChatSession


class ChatSessionForm(forms.ModelForm):
    class Meta:
        model = ChatSession
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "채팅 제목",
                    "class": "text-input",
                }
            )
        }


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "placeholder": "메시지를 입력하세요",
                    "rows": 2,
                    "class": "message-input",
                }
            )
        }
