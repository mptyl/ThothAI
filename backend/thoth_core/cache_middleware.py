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

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

class NoCacheMiddleware(MiddlewareMixin):
    """
    Middleware per aggiungere headers anti-cache alle API responses
    """
    
    def process_response(self, request, response):
        # Applica headers anti-cache solo alle API endpoints
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['X-Data-Timestamp'] = timezone.now().isoformat()
            
            # Aggiungi header per indicare che i dati sono sempre freschi
            response['X-Cache-Status'] = 'no-cache'
        
        return response
