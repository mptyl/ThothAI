from django import forms
from django.contrib import admin
from thoth_core.models import Setting, AiModel
from thoth_core.utilities.utils import export_csv, import_csv

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'theme', 'language')
    search_fields = ('name',)
    ordering = ('name',)
    actions = (export_csv, import_csv)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'theme', 'language'),
            'description': 'Basic settings for the workspace.'
        }),
        ('AI Model Configuration', {
            'fields': ('comment_model', 'system_prompt'),
            'description': 'Configure AI models and prompts for different tasks.'
        }),
        ('Comment Generation Settings', {
            'fields': ('example_rows_for_comment',),
            'classes': ('collapse',),
            'description': 'Settings for AI comment generation.'
        }),
        ('LSH Similarity Settings', {
            'fields': (
                'signature_size', 
                'n_grams', 
                'threshold', 
                'lsh_top_n',
                'edit_distance_threshold',
                'embedding_similarity_threshold',
                'max_examples_per_column',
                'verbose', 
                'use_value_description'
            ),
            'classes': ('collapse',),
            'description': 'Configure LSH similarity search parameters and filtering thresholds.'
        }),
        ('Schema Linking Settings', {
            'fields': ('max_columns_before_schema_linking', 'max_context_usage_before_linking'),
            'classes': ('collapse',),
            'description': 'Configure schema linking behavior based on database complexity and context window usage.'
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'comment_model':
            kwargs["queryset"] = AiModel.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)