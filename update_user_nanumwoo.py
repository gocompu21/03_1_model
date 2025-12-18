import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User


def update_user_name():
    try:
        user = User.objects.get(username="nanumwoo")
        user.first_name = "박희정"
        user.last_name = ""  # Clear last name to avoid confusion as template uses first_name only currently?
        # Actually user said "first name" to "박희정". I'll stick to that.
        # But if last_name exists and template is {{ first_name }}, it's fine.
        # However, standard Korean splitting usually puts family name in last_name.
        # Given the user modified template to only show first_name, I will put the full name there.
        user.save()
        print(
            f"Successfully updated user '{user.username}' first_name to '{user.first_name}'"
        )
    except User.DoesNotExist:
        print("User 'nanumwoo' not found.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    update_user_name()
