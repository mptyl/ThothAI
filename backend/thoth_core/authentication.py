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


import base64
import json
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from rest_framework.authentication import TokenAuthentication

from thoth_core.models import SupabaseSession


def _decode_jwt_exp(token: str):
    """
    Legge il campo 'exp' dal payload JWT decodificando il base64.
    Non verifica la firma — la verifica è già stata fatta da GoTrue
    al momento del login. Usato solo per calcolare la scadenza locale.
    """
    try:
        payload_b64 = token.split(".")[1]
        # Aggiunge padding se necessario (JWT usa base64url senza padding)
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        exp = payload.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(exp, tz=dt_timezone.utc)
    except Exception:
        return None


class SupabaseAwareTokenAuthentication(TokenAuthentication):
    """
    Estende DRF TokenAuthentication per invalidare automaticamente il token
    quando la sessione Supabase associata all'utente è scaduta.

    Se l'utente non ha una SupabaseSession (es. utente Django nativo creato
    con createsuperuser), il comportamento è identico a TokenAuthentication.

    Viene usata al posto di TokenAuthentication solo se SUPABASE_AUTH_ENABLED=True
    (configurato dinamicamente in settings.py).
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        if not settings.SUPABASE_AUTH_ENABLED:
            return (user, token)

        try:
            session = user.supabase_session
            if session.is_expired():
                token.delete()
                raise AuthenticationFailed(
                    "Supabase session expired. Re-authenticate via Athena."
                )
        except SupabaseSession.DoesNotExist:
            # Utente Django nativo (es. bootstrap superuser) — nessun check scadenza
            pass

        return (user, token)
