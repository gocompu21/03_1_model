import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import glossary.models as gm
import exam.models as em

name = '수목해충학'

try:
    gs = gm.Subject.objects.get(name=name)
    print(f"Glossary Subject '{name}': ID {gs.id}")
except gm.Subject.DoesNotExist:
    print(f"Glossary Subject '{name}' NOT FOUND")

try:
    es = em.Subject.objects.get(name=name)
    print(f"Exam Subject '{name}': ID {es.id}")
except em.Subject.DoesNotExist:
    print(f"Exam Subject '{name}' NOT FOUND")
