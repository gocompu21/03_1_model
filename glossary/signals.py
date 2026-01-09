from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from .models import Term
from .utils import clear_subject_term_cache

@receiver([post_save, post_delete], sender=Term)
def term_changed(sender, instance, **kwargs):
    """
    용어가 변경되면 관련 과목의 캐시를 삭제
    """
    # M2M 필드는 post_save에서 아직 설정되지 않았을 수 있음
    # 하지만 단순 word/content 수정 시에는 여기서 처리
    for subject in instance.subjects.all():
        clear_subject_term_cache(subject.name)

@receiver(m2m_changed, sender=Term.subjects.through)
def term_subjects_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    용어의 과목이 변경되면 캐시 삭제
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        # instance는 Term일 수도 있고 Subject일 수도 있음 (reverse에 따라 다름)
        if reverse:
            # Subject instance에서 Term이 변경됨 -> 해당 Subject 캐시 삭제
            clear_subject_term_cache(instance.name)
        else:
            # Term instance에서 Subject가 변경됨 -> 변경된 Subject들의 캐시 삭제
            # pk_set에 포함된 Subject ID들과, 이미 연결된 Subject들 모두 고려
            from .models import Subject
            
            # 1. 이미 연결된 Subject들
            for subject in instance.subjects.all():
                clear_subject_term_cache(subject.name)
            
            # 2. 이번에 추가/삭제된 Subject들
            if pk_set:
                subjects = Subject.objects.filter(pk__in=pk_set)
                for subject in subjects:
                    clear_subject_term_cache(subject.name)
