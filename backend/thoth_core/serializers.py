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

from django.contrib.auth.models import User, Group
from .models import  Workspace, SqlDb, VectorDb, AiModel, BasicAiModel, SqlTable, SqlColumn, Setting, Agent, GroupProfile, ThothLog
from rest_framework import serializers
from thoth_core.models import GroupProfile

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    group_profiles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups', 'group_profiles']
        # Escludiamo campi sensibili come la password

    def get_groups(self, obj):
        return list(obj.groups.values_list('name', flat=True))
    
    def get_group_profiles(self, obj):
        profiles = []
        for group in obj.groups.all():
            # Refresh the group profile from the database to ensure we get the latest data
            try:
                # Get a fresh instance of the profile directly from the database
                profile = GroupProfile.objects.get(group=group)
                profiles.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'show_sql': profile.show_sql,
                    'explain_generated_query': profile.explain_generated_query,
                })
            except GroupProfile.DoesNotExist:
                # Handle the case where a group doesn't have a profile
                pass
        return profiles

class VectorDbSerializer(serializers.ModelSerializer):
    # Add computed fields to indicate if embedding is properly configured
    embedding_configured = serializers.SerializerMethodField()
    has_api_key = serializers.SerializerMethodField()
    
    class Meta:
        model = VectorDb
        fields = [
            'name', 'vect_type', 'host', 'port',
            'embedding_provider', 'embedding_model', 
            'embedding_base_url', 'embedding_batch_size', 
            'embedding_timeout', 'embedding_configured', 'has_api_key'
        ]
    
    def get_embedding_configured(self, obj):
        """Check if embedding is properly configured via model or environment"""
        return self.get_has_api_key(obj) and bool(obj.embedding_provider) and bool(obj.embedding_model)
    
    def get_has_api_key(self, obj):
        """Check if API key exists in environment variables"""
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Check environment variables based on provider
        env_key_mappings = {
            'openai': ['OPENAI_API_KEY', 'OPENAI_KEY'],
            'cohere': ['COHERE_API_KEY', 'COHERE_KEY'],
            'mistral': ['MISTRAL_API_KEY', 'MISTRAL_KEY'],
            'huggingface': ['HUGGINGFACE_API_KEY', 'HF_API_KEY', 'HUGGINGFACE_TOKEN'],
            'anthropic': ['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY']
        }
        
        provider_keys = env_key_mappings.get(obj.embedding_provider, [])
        for env_key in provider_keys:
            if os.environ.get(env_key):
                logger.info(f"VectorDb {obj.name}: API key found in environment variable {env_key}")
                return True
        
        # Also check generic embedding API key
        if os.environ.get('EMBEDDING_API_KEY'):
            logger.info(f"VectorDb {obj.name}: API key found in EMBEDDING_API_KEY")
            return True
        
        logger.warning(f"VectorDb {obj.name}: No API key found for provider {obj.embedding_provider}")
        logger.warning(f"Checked environment variables: {provider_keys + ['EMBEDDING_API_KEY']}")
        return False

class SqlDbSerializer(serializers.ModelSerializer):
    vector_db = VectorDbSerializer(read_only=True)

    class Meta:
        model = SqlDb
        fields = [
            'name', 'db_host', 'db_type', 'db_name', 
            'db_port', 'schema', 'db_mode', 'language', 'vector_db'
        ]

class BasicAiModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BasicAiModel
        fields = '__all__'

class AiModelSerializer(serializers.ModelSerializer):
    basic_model = BasicAiModelSerializer()

    class Meta:
        model = AiModel
        fields = '__all__'

class AgentSerializer(serializers.ModelSerializer):
    ai_model = AiModelSerializer()

    class Meta:
        model = Agent
        fields = ['id', 'name', 'agent_type', 'ai_model', 'temperature', 'top_p', 'max_tokens', 'timeout', 'retries']

class SettingSerializer(serializers.ModelSerializer):
    comment_model = AiModelSerializer()

    class Meta:
        model = Setting
        fields = '__all__'

class WorkspaceSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    sql_db = SqlDbSerializer()
    default_workspace = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    default_model = AiModelSerializer()
    question_validator = AgentSerializer()
    kw_sel_agent = AgentSerializer()
    sql_basic_agent = AgentSerializer()
    sql_advanced_agent = AgentSerializer()
    sql_expert_agent = AgentSerializer()
    test_gen_agent_1 = AgentSerializer()
    test_gen_agent_2 = AgentSerializer()
    test_exec_agent = AgentSerializer()
    explain_sql_agent = AgentSerializer()
    ask_human_help_agent = AgentSerializer()
    setting = SettingSerializer()

    class Meta:
        model = Workspace
        fields = [
            'id',
            'name',
            'level',
            'description',
            'sql_db',
            'setting',
            'default_model',
            'question_validator',
            'kw_sel_agent',
            'sql_basic_agent',
            'sql_advanced_agent',
            'sql_expert_agent',
            'test_gen_agent_1',
            'test_gen_agent_2',
            'test_exec_agent',
            'explain_sql_agent',
            'ask_human_help_agent',
            'default_workspace',
            'users',
            'number_of_tests_to_generate',
            'number_of_sql_to_generate',
            'created_at',
            'updated_at'
        ]


class WorkspaceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for workspace list - returns only id and name"""
    
    class Meta:
        model = Workspace
        fields = ['id', 'name']


class SqlTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = SqlTable
        fields = '__all__'

class SqlColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SqlColumn
        fields = ['id', 'original_column_name', 'column_description', 'data_format', 'generated_comment','value_description', 'pk_field', 'fk_field']


class SqlFullTableSerializer(serializers.ModelSerializer):
    columns = SqlColumnSerializer(many=True, read_only=True, source='sqlcolumn_set')

    class Meta:
        model = SqlTable
        fields = ['id', 'name', 'generated_comment', 'columns']


class SqlTableUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SqlTable
        fields = ['generated_comment']

class SqlColumnUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    generated_comment = serializers.CharField(allow_blank=True)

class SqlColumnBulkUpdateSerializer(serializers.Serializer):
    columns = SqlColumnUpdateSerializer(many=True)

class GroupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupProfile
        fields = ['show_sql', 'explain_generated_query']

class ThothLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThothLog
        fields = '__all__'
        # read_only_fields removed - we need to allow creating logs via API
