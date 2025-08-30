# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from django.db.models import ForeignKey, ManyToManyField, OneToOneField
import csv
import os


class Command(BaseCommand):
    help = 'Import a single CSV file into the corresponding Django model'

    def add_arguments(self, parser):
        parser.add_argument('model_name', type=str, help='Name of the model to import')

    def handle(self, *args, **options):
        model_name = options['model_name']
        Model = apps.get_model('toth_be', model_name)
        file_path = os.path.join('exports', f"{model_name.lower()}.csv")

        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                with transaction.atomic():
                    instance_data = {}
                    m2m_data = {}

                    for field_name, value in row.items():
                        field = Model._meta.get_field(field_name)
                        if isinstance(field, (ForeignKey, OneToOneField)):
                            if value.strip():
                                instance_data[field_name] = field.related_model.objects.get(pk=value.strip())
                        elif isinstance(field, ManyToManyField):
                            if value.strip():
                                m2m_data[field_name] = [int(id.strip()) for id in value.split(',') if id.strip()]
                        else:
                            instance_data[field_name] = value

                    pk_field = Model._meta.pk.original_column_name
                    pk_value = instance_data.get(pk_field, '').strip()
                    if pk_value:
                        instance, _ = Model.objects.update_or_create(
                            **{pk_field: pk_value},
                            defaults=instance_data
                        )
                    else:
                        instance = Model.objects.create(**{k: v for k, v in instance_data.items() if k != pk_field})

                    for field_name, ids in m2m_data.items():
                        getattr(instance, field_name).set(ids)

        self.stdout.write(self.style.SUCCESS(f'Successfully imported data for {model_name}'))
