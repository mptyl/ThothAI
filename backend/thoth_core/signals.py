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

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(user_logged_in)
def set_default_workspace_on_login(sender, user, request, **kwargs):
    """
    After login, set the user's first default workspace in the session (if it exists)
    and save the authentication token for passing to the frontend.
    """
    default_ws = user.default_workspaces.first()
    if default_ws:
        request.session['selected_workspace_id'] = default_ws.pk
    
    # Get or create token for the user and save it in session
    token, created = Token.objects.get_or_create(user=user)
    request.session['auth_token'] = token.key
