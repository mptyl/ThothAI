from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin, UserAdmin as BaseUserAdmin
from thoth_core.models import GroupProfile
from thoth_core.utilities.utils import export_csv, import_csv

class GroupProfileInline(admin.StackedInline):
    model = GroupProfile
    max_num = 1
    min_num = 1
    can_delete = False
    extra = 0
    verbose_name = "Group Profile Settings"
    verbose_name_plural = "Group Profile Settings"
    fields = [
        'show_sql',
        'explain_generated_query',
    ]
    # metodi custom da copiare qui dal file originale

class GroupAdmin(BaseGroupAdmin):
    inlines = [GroupProfileInline]
    actions = [export_csv, import_csv]
    # BaseGroupAdmin.fieldsets is None, so we need to define our own
    fieldsets = (
        (None, {'fields': ('name', 'permissions')}),
    )

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
    list_display = ('group_name', 'show_sql', 'explain_generated_query')
    list_filter = ('show_sql', 'explain_generated_query')
    search_fields = ('group__name',)
    ordering = ('group__name',)
    actions = (export_csv, import_csv)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "group":
            kwargs["queryset"] = Group.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def group_name(self, obj):
        """Display the group name."""
        return obj.group.name if obj.group else "-"
    group_name.short_description = 'Group'
    group_name.admin_order_field = 'group__name'