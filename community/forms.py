from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content"]
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
                    "placeholder": "마크다운으로 내용을 작성하세요",
                    "rows": 16,
                }
            ),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "community-comment-textarea",
                    "placeholder": "댓글을 입력하세요",
                    "rows": 3,
                }
            ),
        }
        labels = {
            "content": "댓글",
        }
