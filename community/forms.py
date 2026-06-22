from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "image"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "community-input",
                    "placeholder": "제목을 입력하세요",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "community-textarea",
                    "placeholder": "내용을 입력하세요",
                    "rows": 12,
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "community-file-input",
                    "accept": "image/jpeg,image/png,image/gif,image/webp",
                }
            ),
        }
