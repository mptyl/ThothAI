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
        # Force immediate logging to stderr to bypass Django logging
        import sys

        print("=" * 50, file=sys.stderr)
        print("ApiKeyAuthentication.authenticate() CALLED", file=sys.stderr)
        print(f"Request type: {type(request)}", file=sys.stderr)
        print(
            f"Request headers attribute exists: {hasattr(request, 'headers')}",
            file=sys.stderr,
        )

        api_key = request.headers.get("X-API-KEY")
        print(
            f"API key from headers: {api_key[:10] if api_key else 'None'}...",
            file=sys.stderr,
        )
        print(
            f"Settings API_KEY: {settings.API_KEY[:10] if settings.API_KEY else 'None'}...",
            file=sys.stderr,
        )

        if not api_key:
            print("No API key in headers, returning None", file=sys.stderr)
            return None

        if api_key != settings.API_KEY:
            print(f"Invalid API key! Received: {api_key}", file=sys.stderr)
            print(f"Expected: {settings.API_KEY}", file=sys.stderr)
            raise AuthenticationFailed("Invalid API key")

        print("Valid API key! Returning (None, True)", file=sys.stderr)
        return (None, True)
