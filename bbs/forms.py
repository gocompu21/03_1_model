from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content"]
        widgets = {
            "title": forms.Textarea(
                attrs={"class": "form-control", "id": "summernote-title", "rows": 1}
            ),
            "content": forms.Textarea(
                attrs={"class": "form-control", "id": "summernote"}
            ),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "댓글을 입력하세요",
                }
            ),
        }
