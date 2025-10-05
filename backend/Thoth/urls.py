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
URL configuration for Thoth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include

# Customize admin site
admin.site.site_header = "Thoth Administration"
admin.site.site_title = "Thoth Admin"
admin.site.index_title = "Welcome to Thoth Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("thoth_core.urls", "thoth_core"), namespace="thoth_core")),
    path("vdb/", include("thoth_ai_backend.urls")),
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG and "django_browser_reload" in settings.INSTALLED_APPS:
    urlpatterns.append(path("__reload__/", include("django_browser_reload.urls")))
