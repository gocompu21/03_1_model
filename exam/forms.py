from django import forms
from .models import Question
from django.contrib.auth.forms import AuthenticationForm


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            "exam",
            "subject",
            "number",
            "content",
            "image",
            "choice1",
            "choice2",
            "choice3",
            "choice4",
            "choice5",
            "answer",
            "general_chat",
            "textbook_chat",
            "infographic_image",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3}),
            "general_chat": forms.Textarea(attrs={"rows": 3}),
            "textbook_chat": forms.Textarea(attrs={"rows": 3}),
            "choice1": forms.TextInput(attrs={"class": "form-control"}),
            "choice2": forms.TextInput(attrs={"class": "form-control"}),
            "choice3": forms.TextInput(attrs={"class": "form-control"}),
            "choice4": forms.TextInput(attrs={"class": "form-control"}),
            "choice5": forms.TextInput(attrs={"class": "form-control"}),
        }
