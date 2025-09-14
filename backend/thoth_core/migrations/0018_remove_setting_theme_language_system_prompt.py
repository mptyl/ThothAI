from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("thoth_core", "0017_remove_setting_comment_model_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="setting",
            name="theme",
        ),
        migrations.RemoveField(
            model_name="setting",
            name="language",
        ),
        migrations.RemoveField(
            model_name="setting",
            name="system_prompt",
        ),
    ]

