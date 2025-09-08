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

import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

logger = logging.getLogger(__name__)


class ApiKeyAuthentication(BaseAuthentication):
    """
    Custom authentication class that authenticates requests based on API key.
    """

    def authenticate(self, request):
        api_key = request.headers.get("X-API-KEY")
        
        if not api_key:
            return None

        if api_key != settings.API_KEY:
            logger.debug(f"Invalid API key received")
            raise AuthenticationFailed("Invalid API key")

        logger.debug("Valid API key authentication")
        return (None, True)
