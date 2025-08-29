from django import forms
from django.contrib import admin
from thoth_core.models import AiModel, BasicAiModel
from thoth_core.utilities.utils import export_csv, import_csv

class AiModelAdminForm(forms.ModelForm):
    class Meta:
        model = AiModel
        fields = '__all__'
        widgets = {
            'specific_model': forms.TextInput(attrs={'style': 'width: 250px;'}),
            'name': forms.TextInput(attrs={'style': 'width: 500px;'}),
            'url': forms.URLInput(attrs={'style': 'width: 500px;'}),
        }

@admin.register(AiModel)
class AiModelAdmin(admin.ModelAdmin):
    form = AiModelAdminForm
    list_display = ('specific_model', 'get_basic_model', 'name')
    search_fields = ('basic_model__name', 'specific_model', 'name')
    list_filter = ('basic_model__name',)
    ordering = ('name',)
    fieldsets = [
        (
            None,
            {
                "fields": ['basic_model', 'specific_model', 'name', 'url'],
            }
        ),
        (
            "Advanced",
            {
                "classes": ['collapse'],
                "fields": ['temperature_allowed','temperature','top_p','max_tokens','timeout','context_size'],
            }
        ),
    ]
    actions = (export_csv, import_csv)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "basic_model":
            kwargs["queryset"] = BasicAiModel.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_basic_model(self, obj):
        return obj.basic_model.name if obj.basic_model else '-'
    get_basic_model.short_description = 'Basic Model'
    get_basic_model.admin_order_field = 'basic_model__name'