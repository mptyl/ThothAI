from django import forms
from django.contrib import admin
from thoth_core.models import Agent, AiModel
from thoth_core.utilities.utils import export_csv, import_csv

class AgentAdminForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'style': 'width: 400px;'}),
            'temperature': forms.NumberInput(attrs={'style': 'width: 100px;'}),
            'top_p': forms.NumberInput(attrs={'style': 'width: 100px;'}),
            'max_tokens': forms.NumberInput(attrs={'style': 'width: 100px;'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sort agent_type choices alphabetically by display name
        from thoth_core.models import AgentChoices
        sorted_choices = sorted(AgentChoices.choices, key=lambda x: x[1])  # Sort by display name (x[1])
        self.fields['agent_type'].choices = sorted_choices
    
    # clean da copiare qui dal file originale

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    form = AgentAdminForm
    list_display = ('name',  'agent_type', 'get_model', 'temperature', 'top_p', 'max_tokens', 'timeout', 'retries')
    list_filter = ('ai_model__basic_model', 'agent_type')
    search_fields = ('name',)
    ordering = ('name',)
    actions = (export_csv, import_csv)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'agent_type', 'ai_model'),
            'description': 'Configure the basic agent settings.'
        }),
        ('AI Parameters', {
            'fields': ('temperature', 'top_p', 'max_tokens'),
            'description': 'Fine-tune AI model parameters for this agent.'
        }),
        ('Execution Settings', {
            'fields': ('timeout', 'retries'),
            'classes': ('collapse',),
            'description': 'Configure execution timeout and retry behavior.'
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "ai_model":
            kwargs["queryset"] = AiModel.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_model(self, obj):
        """Display the AI model associated with this agent."""
        return obj.ai_model.name if obj.ai_model else "-"
    get_model.short_description = 'AI Model'
    get_model.admin_order_field = 'ai_model__name'