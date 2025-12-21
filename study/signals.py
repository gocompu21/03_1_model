from django.db.models.signals import post_save
from django.dispatch import receiver
from notebook.models import NotebookHistory
from chat.models import ChatHistory
from .models import StudyQnA


@receiver(post_save, sender=NotebookHistory)
def create_study_qna_from_notebook(sender, instance, created, **kwargs):
    if created:
        StudyQnA.objects.create(
            user=instance.user,
            q_type="notebook",
            related_notebook=instance,
            question=instance.user_input,
            answer=instance.ai_response,
            # NotebookHistory doesn't have is_public, default False
        )


@receiver(post_save, sender=ChatHistory)
def create_study_qna_from_chat(sender, instance, created, **kwargs):
    if created:
        StudyQnA.objects.create(
            user=instance.user,
            q_type="chat",
            related_chat=instance,
            question=instance.user_input,
            answer=instance.ai_response,
        )
