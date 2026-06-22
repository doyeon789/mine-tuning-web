from django import forms

from .models import ChatMessage, ChatSession


class ChatSessionForm(forms.ModelForm):
    class Meta:
        model = ChatSession
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Chat title",
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
                    "placeholder": "Ask anything",
                    "rows": 2,
                    "class": "message-input",
                }
            )
        }
