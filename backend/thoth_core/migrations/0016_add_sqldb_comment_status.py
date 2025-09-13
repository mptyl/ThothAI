from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("thoth_core", "0015_alter_sqldb_language_alter_thothlog_db_language_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqldb",
            name="table_comment_status",
            field=models.CharField(
                choices=[
                    ("IDLE", "Idle"),
                    ("RUNNING", "Running"),
                    ("COMPLETED", "Completed"),
                    ("FAILED", "Failed"),
                ],
                default="IDLE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="table_comment_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="table_comment_log",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="table_comment_start_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="table_comment_end_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="column_comment_status",
            field=models.CharField(
                choices=[
                    ("IDLE", "Idle"),
                    ("RUNNING", "Running"),
                    ("COMPLETED", "Completed"),
                    ("FAILED", "Failed"),
                ],
                default="IDLE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="column_comment_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="column_comment_log",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="column_comment_start_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqldb",
            name="column_comment_end_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
