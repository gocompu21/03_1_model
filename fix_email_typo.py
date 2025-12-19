import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    user = User.objects.get(username="gocompu21")
    if user.email == "gocompu21@gmaili.com":
        user.email = "gocompu21@gmail.com"
        user.save()
        print(f"Fixed typo: Email updated to {user.email}")
    else:
        print(f"Email is already: {user.email}")

except User.DoesNotExist:
    print("User not found")
