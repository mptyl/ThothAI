from django.contrib import admin
from thoth_core.models import BasicAiModel
from thoth_core.utilities.utils import export_csv, import_csv

@admin.register(BasicAiModel)
class BasicAiModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'provider')
    search_fields = ('name', 'provider')
    list_filter = ('provider',)
    ordering = ('name',)
    actions = (export_csv, import_csv)