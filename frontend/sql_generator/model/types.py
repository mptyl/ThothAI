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
Common type definitions for the SQL generator models.

This module contains shared type definitions to avoid circular imports.
"""

from typing import Any, Dict, TypedDict


class TableInfo(TypedDict):
    """Type definition for database table information."""
    table_description: str
    columns: Dict[str, Dict[str, Any]]