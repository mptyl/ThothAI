# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces in a string."""
    if value:
        return str(value).replace('_', ' ')
    return value

@register.filter
def format_category_name(value):
    """Format category names by replacing underscores and capitalizing."""
    if value:
        return str(value).replace('_', ' ').title()
    return value