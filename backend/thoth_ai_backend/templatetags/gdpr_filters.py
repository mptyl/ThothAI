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

from django import template

register = template.Library()


@register.filter
def replace_underscore(value):
    """Replace underscores with spaces in a string."""
    if value:
        return str(value).replace("_", " ")
    return value


@register.filter
def format_category_name(value):
    """Format category names by replacing underscores and capitalizing."""
    if value:
        return str(value).replace("_", " ").title()
    return value
