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
Setup for log directories to ensure they exist when the application starts.
"""

import os

def ensure_log_directories():
    """Ensure log directories exist."""
    log_dirs = [
        'logs',
        'logs/db_elements',
    ]
    
    for log_dir in log_dirs:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)