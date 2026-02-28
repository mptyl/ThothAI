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

"""
Tests per l'endpoint POST /api/supabase-auth.
Tutti i test mockano la chiamata HTTP a GoTrue — nessun servizio esterno necessario.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from thoth_core.models import SupabaseSession


# JWT con payload {"sub":"1","exp":9999999999} — anno ~2286, serve per testare exp decode
# ARCHITETTURA ATTESA: il mock "thoth_core.views.requests.get" presuppone che:
# - la view supabase_auth sia in thoth_core/views.py (Task 5)
# - quel modulo usi `import requests` a livello di file (non `from requests import get`)
# Se la view viene spostata in un altro modulo, aggiornare tutti i patch() di seguito.
FAKE_JWT_WITH_EXP = (
    "eyJhbGciOiJIUzI1NiJ9"
    ".eyJzdWIiOiIxIiwiZXhwIjo5OTk5OTk5OTk5fQ"
    ".fake_sig"
)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def supabase_settings(settings):
    """Applica le impostazioni Supabase ai test che la richiedono."""
    settings.SUPABASE_AUTH_ENABLED = True
    settings.SUPABASE_AUTH_URL = "http://fake-supabase-auth:9999"
    settings.DEFAULT_WORKSPACE_NAME = "california_schools"
    return settings


def _make_workspace(name="california_schools"):
    """Helper: crea un Workspace minimo per i test.

    Il modello Workspace ha molte FK (sql_db, default_model, Agent, ecc.) ma
    tutte sono dichiarate con null=True e on_delete=SET_NULL, quindi
    Workspace.objects.create(name=name) è sufficiente — non occorre creare
    prerequisiti aggiuntivi.
    """
    from thoth_core.models import Workspace
    return Workspace.objects.create(name=name)


def _mock_gotrue(email="mario@example.com", full_name="Mario Rossi"):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "email": email,
        "user_metadata": {"full_name": full_name},
    }
    return mock_resp


@pytest.mark.django_db
class TestSupabaseAuthDisabled:

    def test_returns_404_when_disabled(self, client, settings):
        """Endpoint deve essere invisibile se SUPABASE_AUTH_ENABLED=False."""
        settings.SUPABASE_AUTH_ENABLED = False
        res = client.post("/api/supabase-auth",
                          {"token": "any"},
                          format="json")
        assert res.status_code == 404


@pytest.mark.django_db
class TestSupabaseAuthValidation:

    def test_returns_400_when_no_token(self, client, supabase_settings):
        res = client.post("/api/supabase-auth", {}, format="json")
        assert res.status_code == 400
        assert "Token required" in res.data["error"]

    def test_returns_401_when_gotrue_rejects_token(self, client, supabase_settings):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("thoth_core.views.requests.get", return_value=mock_resp):
            res = client.post("/api/supabase-auth",
                              {"token": "bad-jwt"},
                              format="json")
        assert res.status_code == 401
        assert "Invalid" in res.data["error"]

    def test_returns_503_when_gotrue_unreachable(self, client, supabase_settings):
        import requests as req_lib
        with patch("thoth_core.views.requests.get",
                   side_effect=req_lib.RequestException("timeout")):
            res = client.post("/api/supabase-auth",
                              {"token": "any"},
                              format="json")
        assert res.status_code == 503
        assert "error" in res.data  # risposta strutturata, non HTML
        # GoTrue irraggiungibile prima della creazione utente → nessun utente orfano
        assert not User.objects.filter(email="any").exists()

    def test_returns_400_when_email_missing_in_payload(self, client, supabase_settings):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"user_metadata": {}}  # no email
        with patch("thoth_core.views.requests.get", return_value=mock_resp):
            res = client.post("/api/supabase-auth",
                              {"token": "jwt-no-email"},
                              format="json")
        assert res.status_code == 400


@pytest.mark.django_db
class TestSupabaseAuthProvisioning:

    def test_creates_new_user_on_first_login(self, client, supabase_settings):
        _make_workspace()
        assert not User.objects.filter(username="mario@example.com").exists()
        with patch("thoth_core.views.requests.get",
                   return_value=_mock_gotrue()):
            res = client.post("/api/supabase-auth",
                              {"token": FAKE_JWT_WITH_EXP},
                              format="json")
        assert res.status_code == 200
        assert "token" in res.data
        user = User.objects.get(username="mario@example.com")
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.first_name == "Mario"
        assert user.last_name == "Rossi"

    def test_returns_existing_django_token_for_known_user(self, client, supabase_settings):
        """Secondo login: stesso utente, stesso token DRF."""
        _make_workspace()
        with patch("thoth_core.views.requests.get",
                   return_value=_mock_gotrue()):
            res1 = client.post("/api/supabase-auth",
                               {"token": FAKE_JWT_WITH_EXP}, format="json")
            res2 = client.post("/api/supabase-auth",
                               {"token": FAKE_JWT_WITH_EXP}, format="json")
        assert res1.data["token"] == res2.data["token"]
        assert User.objects.filter(username="mario@example.com").count() == 1

    def test_returns_503_and_rolls_back_user_when_workspace_not_found(
        self, client, supabase_settings
    ):
        """
        Se il workspace di default non esiste, deve restituire 503.
        Se l'utente è stato appena creato, deve essere eliminato (rollback).
        """
        email = "newuser_no_workspace@example.com"
        assert not User.objects.filter(username=email).exists()

        supabase_settings.DEFAULT_WORKSPACE_NAME = "workspace_inesistente"
        with patch("thoth_core.views.requests.get",
                   return_value=_mock_gotrue(email=email)):
            res = client.post("/api/supabase-auth",
                              {"token": FAKE_JWT_WITH_EXP},
                              format="json")

        assert res.status_code == 503
        assert res.data["error"] == "setup_incomplete"
        assert "workspace_inesistente" in res.data["detail"]
        # Rollback: l'utente NON deve esistere
        assert not User.objects.filter(username=email).exists()

    def test_no_rollback_for_existing_user_when_workspace_not_found(
        self, client, supabase_settings
    ):
        """
        Per un utente già esistente, il workspace non viene assegnato nuovamente
        (la logica è: `if created: workspace.users.add(user)`).
        Quindi, anche se il workspace non esiste, un utente preesistente ottiene 200
        e non viene toccato — il rollback è solo per gli utenti appena creati.
        """
        email = "existing@example.com"
        user = User.objects.create_user(username=email, email=email, password="x")
        Token.objects.create(user=user)

        # Il secondo accesso non assegna workspace (only if created)
        # quindi workspace mancante non causa 503
        with patch("thoth_core.views.requests.get",
                   return_value=_mock_gotrue(email=email)):
            res = client.post("/api/supabase-auth",
                              {"token": FAKE_JWT_WITH_EXP},
                              format="json")

        assert res.status_code == 200
        assert User.objects.filter(username=email).exists()


@pytest.mark.django_db
class TestSupabaseSession:

    def test_supabase_session_created_on_first_login(self, client, supabase_settings):
        """Al primo login deve essere creata una SupabaseSession."""
        _make_workspace()
        with patch("thoth_core.views.requests.get",
                   return_value=_mock_gotrue(email="session_user@example.com")):
            res = client.post("/api/supabase-auth",
                              {"token": FAKE_JWT_WITH_EXP},
                              format="json")
        assert res.status_code == 200
        user = User.objects.get(username="session_user@example.com")
        session = SupabaseSession.objects.get(user=user)
        assert not session.is_expired()
        assert session.expires_at.year > 2200

    def test_supabase_session_count_is_one_after_multiple_logins(
        self, client, supabase_settings
    ):
        """Più login → una sola SupabaseSession per utente (update_or_create)."""
        _make_workspace()
        with patch("thoth_core.views.requests.get",
                   return_value=_mock_gotrue(email="session_user@example.com")):
            client.post("/api/supabase-auth",
                        {"token": FAKE_JWT_WITH_EXP}, format="json")
            client.post("/api/supabase-auth",
                        {"token": FAKE_JWT_WITH_EXP}, format="json")

        assert SupabaseSession.objects.filter(
            user__username="session_user@example.com"
        ).count() == 1

    def test_no_session_when_jwt_has_no_exp(self, client, supabase_settings):
        """Se il JWT non contiene 'exp', non deve essere creata la SupabaseSession."""
        _make_workspace()
        # JWT con payload {"sub":"1"} senza exp
        jwt_no_exp = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.fake"
        email = "noexp@example.com"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"email": email, "user_metadata": {}}

        with patch("thoth_core.views.requests.get", return_value=mock_resp):
            res = client.post("/api/supabase-auth",
                              {"token": jwt_no_exp},
                              format="json")
        assert res.status_code == 200
        assert not SupabaseSession.objects.filter(user__username=email).exists()
