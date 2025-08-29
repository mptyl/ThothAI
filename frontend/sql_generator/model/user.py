# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

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
