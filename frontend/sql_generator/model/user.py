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

class Group:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class User:
    def __init__(self, id, username, email, groups, first_name="", last_name="", group_profiles=None):
        self.id=id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.groups = groups
        self.group_profiles = group_profiles or []

    def __str__(self):
        return self.username
