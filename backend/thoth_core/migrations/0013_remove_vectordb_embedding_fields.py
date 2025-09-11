from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('thoth_core', '0012_add_escalation_flags'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vectordb',
            name='embedding_base_url',
        ),
        migrations.RemoveField(
            model_name='vectordb',
            name='embedding_batch_size',
        ),
        migrations.RemoveField(
            model_name='vectordb',
            name='embedding_model',
        ),
        migrations.RemoveField(
            model_name='vectordb',
            name='embedding_provider',
        ),
        migrations.RemoveField(
            model_name='vectordb',
            name='embedding_timeout',
        ),
    ]
