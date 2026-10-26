import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="chat/%Y/%m/", verbose_name="사진")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("history", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="chat.chathistory")),
            ],
            options={
                "verbose_name": "질문 사진",
                "verbose_name_plural": "질문 사진 목록",
                "ordering": ["id"],
            },
        ),
    ]
