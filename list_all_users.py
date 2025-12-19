import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("--- User List ---")
for user in User.objects.all():
    print(f"ID: '{user.username}'")
    print(f"Name (first_name): '{user.first_name}'")
    print(f"Email: '{user.email}'")
    print(f"Active: {user.is_active}")
    print("-" * 20)
