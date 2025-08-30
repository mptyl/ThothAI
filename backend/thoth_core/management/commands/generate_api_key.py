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

import secrets
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a new API key for authentication"

    def handle(self, *args, **kwargs):
        api_key = secrets.token_urlsafe(32)
        self.stdout.write(self.style.SUCCESS(f"Generated API Key: {api_key}"))
