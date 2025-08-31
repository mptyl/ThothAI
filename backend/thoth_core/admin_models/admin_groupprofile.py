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

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from thoth_core.models import GroupProfile
from thoth_core.utilities.utils import export_csv, import_csv


class GroupProfileInline(admin.StackedInline):
    model = GroupProfile
    max_num = 1
    min_num = 1  # Always show the form
    can_delete = False
    extra = 1  # Show one form for new groups
    verbose_name = "Group Profile Settings"
    verbose_name_plural = "Group Profile Settings"
    fields = [
        "show_sql",
        "explain_generated_query",
    ]
    
    def get_extra(self, request, obj=None, **kwargs):
        """Show extra form only for new groups."""
        if obj:
            # Existing group - check if profile exists
            if not hasattr(obj, 'profile'):
                return 1
            return 0
        # New group
        return 1
    
    def get_min_num(self, request, obj=None, **kwargs):
        """Always require at least one profile."""
        return 0 if obj and hasattr(obj, 'profile') else 1


class GroupAdmin(BaseGroupAdmin):
    inlines = [GroupProfileInline]
    actions = [export_csv, import_csv]
    # BaseGroupAdmin.fieldsets is None, so we need to define our own
    fieldsets = ((None, {"fields": ("name", "permissions")}),)
    
    def save_model(self, request, obj, form, change):
        """Mark that we're saving from admin to skip signal."""
        obj._from_admin = True
        super().save_model(request, obj, form, change)


# Unregister the default Group admin and register our custom one
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)

# Unregister the default User admin and register our custom one with CSV actions
admin.site.unregister(User)


class UserAdmin(BaseUserAdmin):
    actions = list(BaseUserAdmin.actions) + [export_csv, import_csv]


admin.site.register(User, UserAdmin)


@admin.register(GroupProfile)
class GroupProfileAdmin(admin.ModelAdmin):
    list_display = ("group_name", "show_sql", "explain_generated_query")
    list_filter = ("show_sql", "explain_generated_query")
    search_fields = ("group__name",)
    ordering = ("group__name",)
    actions = (export_csv, import_csv)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "group":
            kwargs["queryset"] = Group.objects.all().order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def group_name(self, obj):
        """Display the group name."""
        return obj.group.name if obj.group else "-"

    group_name.short_description = "Group"
    group_name.admin_order_field = "group__name"
