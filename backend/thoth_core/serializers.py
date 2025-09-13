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
from .models import (
    Workspace,
    SqlDb,
    VectorDb,
    AiModel,
    BasicAiModel,
    SqlTable,
    SqlColumn,
    Setting,
    Agent,
    GroupProfile,
    ThothLog,
)
from rest_framework import serializers
from thoth_core.models import GroupProfile


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    group_profiles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "groups",
            "group_profiles",
        ]
        # Escludiamo campi sensibili come la password

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    def get_group_profiles(self, obj):
        profiles = []
        for group in obj.groups.all():
            # Refresh the group profile from the database to ensure we get the latest data
            try:
                # Get a fresh instance of the profile directly from the database
                profile = GroupProfile.objects.get(group=group)
                profiles.append(
                    {
                        "group_id": group.id,
                        "group_name": group.name,
                        "show_sql": profile.show_sql,
                        "explain_generated_query": profile.explain_generated_query,
                    }
                )
            except GroupProfile.DoesNotExist:
                # Handle the case where a group doesn't have a profile
                pass
        return profiles


class VectorDbSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorDb
        fields = [
            "name",
            "vect_type",
            "host",
            "port"
        ]


class SqlDbSerializer(serializers.ModelSerializer):
    vector_db = VectorDbSerializer(read_only=True)

    class Meta:
        model = SqlDb
        fields = [
            "name",
            "db_host",
            "db_type",
            "db_name",
            "db_port",
            "schema",
            "db_mode",
            "language",
            "vector_db",
        ]


class BasicAiModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BasicAiModel
        fields = "__all__"


class AiModelSerializer(serializers.ModelSerializer):
    basic_model = BasicAiModelSerializer()

    class Meta:
        model = AiModel
        fields = "__all__"


class AgentSerializer(serializers.ModelSerializer):
    ai_model = AiModelSerializer()

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "agent_type",
            "ai_model",
            "temperature",
            "top_p",
            "max_tokens",
            "timeout",
            "retries",
        ]


class SettingSerializer(serializers.ModelSerializer):
    language_display = serializers.CharField(source="get_language_display", read_only=True)

    class Meta:
        model = Setting
        fields = "__all__"
        read_only_fields = getattr(getattr(Setting, "Meta", object), "read_only_fields", tuple())


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
    test_gen_agent_3 = AgentSerializer()
    test_evaluator_agent = AgentSerializer()
    explain_sql_agent = AgentSerializer()
    ask_human_help_agent = AgentSerializer()
    setting = SettingSerializer()
    embedding_config = serializers.SerializerMethodField()

    # Override level field to return only the string value, not the tuple
    level = serializers.SerializerMethodField()

    def get_level(self, obj):
        """Return only the string value of the level choice field."""
        return obj.level

    def get_embedding_config(self, obj):
        import os

        return {
            "provider": os.environ.get("EMBEDDING_PROVIDER"),
            "model": os.environ.get("EMBEDDING_MODEL"),
            "has_api_key": bool(os.environ.get("EMBEDDING_API_KEY")),
            "base_url": os.environ.get("EMBEDDING_BASE_URL", ""),
            "batch_size": os.environ.get("EMBEDDING_BATCH_SIZE", "100"),
            "timeout": os.environ.get("EMBEDDING_TIMEOUT", "30"),
        }

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "level",
            "description",
            "sql_db",
            "setting",
            "default_model",
            "question_validator",
            "kw_sel_agent",
            "sql_basic_agent",
            "sql_advanced_agent",
            "sql_expert_agent",
            "test_gen_agent_1",
            "test_gen_agent_2",
            "test_gen_agent_3",
            "test_evaluator_agent",
            "explain_sql_agent",
            "ask_human_help_agent",
            "default_workspace",
            "users",
            "number_of_tests_to_generate",
            "number_of_sql_to_generate",
            "evaluation_threshold",
            "belt_and_suspenders",
            "created_at",
            "updated_at",
            "embedding_config",
        ]


class WorkspaceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for workspace list - returns only id and name"""

    class Meta:
        model = Workspace
        fields = ["id", "name"]


class SqlTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = SqlTable
        fields = "__all__"


class SqlColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SqlColumn
        fields = [
            "id",
            "original_column_name",
            "column_description",
            "data_format",
            "generated_comment",
            "value_description",
            "pk_field",
            "fk_field",
        ]


class SqlFullTableSerializer(serializers.ModelSerializer):
    columns = SqlColumnSerializer(many=True, read_only=True, source="sqlcolumn_set")

    class Meta:
        model = SqlTable
        fields = ["id", "name", "generated_comment", "columns"]


class SqlTableUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SqlTable
        fields = ["generated_comment"]


class SqlColumnUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    generated_comment = serializers.CharField(allow_blank=True)


class SqlColumnBulkUpdateSerializer(serializers.Serializer):
    columns = SqlColumnUpdateSerializer(many=True)


class GroupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupProfile
        fields = ["show_sql", "explain_generated_query"]


class ThothLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThothLog
        fields = "__all__"
        # read_only_fields removed - we need to allow creating logs via API
