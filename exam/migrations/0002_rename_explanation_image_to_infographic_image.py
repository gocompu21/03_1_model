from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exam", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="question",
            old_name="explanation_image",
            new_name="infographic_image",
        ),
        migrations.AlterField(
            model_name="question",
            name="infographic_image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="questions/explanations/",
                verbose_name="인포그래픽 이미지",
            ),
        ),
    ]
