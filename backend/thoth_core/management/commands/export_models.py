# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.apps import apps
import csv
import os

class Command(BaseCommand):
    help = 'Export all model data to CSV files in IO_DIR'

    def handle(self, *args, **options):
        io_dir = os.getenv('IO_DIR', 'exports')

        if not io_dir:
            self.stdout.write(self.style.ERROR('IO_DIR not set in .env file'))
            return

        os.makedirs(io_dir, exist_ok=True)

        app_models = apps.get_app_config('thoth_core').get_models()

        for Model in app_models:
            model_name = Model.__name__
            file_path = os.path.join(io_dir, f"{model_name.lower()}.csv")

            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                fields = [f.name for f in Model._meta.fields]
                m2m_fields = [f.name for f in Model._meta.many_to_many]
                writer.writerow(fields + m2m_fields)

                for obj in Model.objects.all():
                    row = []
                    for field in fields:
                        value = getattr(obj, field)
                        if field.endswith('_id'):
                            row.append(value)
                        elif hasattr(value, 'pk'):
                            row.append(value.pk)
                        else:
                            row.append(value)
                    for m2m_field in m2m_fields:
                        related_objects = getattr(obj, m2m_field).all()
                        row.append(','.join(str(related.pk) for related in related_objects))
                    writer.writerow(row)

            self.stdout.write(self.style.SUCCESS(f'Exported {model_name} to {file_path}'))
