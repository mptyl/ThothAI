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
Test-specific Django settings.

Overrides the database configuration to use the direct PostgreSQL port (5433),
bypassing the Supabase connection pooler (5432) which does not support the
CREATE DATABASE DDL command required by pytest-django to create the test database.

Usage:
    pytest --ds=Thoth.settings_test tests/test_supabase_auth.py

Or set DJANGO_SETTINGS_MODULE=Thoth.settings_test in the test environment.
"""

import os

# Point DATABASE_URL to direct PostgreSQL (port 5433) before settings.py loads.
# load_dotenv(override=True) in settings.py would otherwise overwrite this,
# so we set it here and rely on the fact that settings_test.py is imported first.
#
# Fetch credentials from the existing .env.local URL but switch to port 5433
# (Supabase direct PostgreSQL, supports CREATE DATABASE).
#
# Default: use the same credentials as .env.local but via direct port.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgres://postgres:postgres@127.0.0.1:5433/postgres",
)

# Now import everything from the main settings module.
# load_dotenv(override=True) in settings.py WILL override DATABASE_URL again,
# so we re-override it after the import.
from Thoth.settings import *  # noqa: F401, F403, E402

# Re-apply the test database URL after load_dotenv has run.
import dj_database_url  # noqa: E402

_test_db_url = os.environ.get(
    "TEST_DATABASE_URL",
    "postgres://postgres:postgres@127.0.0.1:5433/postgres",
)

# Use dj_database_url.parse() (not .config()) so the DATABASE_URL env var
# set by load_dotenv(override=True) in settings.py is NOT consulted.
DATABASES = {
    "default": dj_database_url.parse(
        _test_db_url,
        conn_max_age=0,
    )
}

# Add schema support matching main settings
_db_schema = os.environ.get("DB_SCHEMA", "thoth_schema")
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["options"] = f"-c search_path={_db_schema},public"

# Disable password hashers for speed in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable email sending in tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
