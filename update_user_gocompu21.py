import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    user = User.objects.get(username="gocompu21")
    user.first_name = "김상현"
    user.email = "gocompu21@gmaili.com"  # As requested
    user.save()
    print(
        f"Successfully updated user {user.username}: Name={user.first_name}, Email={user.email}"
    )
except User.DoesNotExist:
    print("User 'gocompu21' does not exist.")
except Exception as e:
    print(f"Error: {e}")
