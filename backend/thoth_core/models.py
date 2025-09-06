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

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver


class AgentChoices(models.TextChoices):
    EXTRACTKEYWORDS = "EXTRACTKEYWORDS", "Keywords Extractor"
    SQLBASIC = "SQLBASIC", "SQL Generator - Basic"
    SQLADVANCED = "SQLADVANCED", "SQL Generator - Advanced"
    SQLEXPERT = "SQLEXPERT", "SQL Generator - Expert"
    TESTGENERATORBASIC = "TESTGENERATORBASIC", "Test Generator - Basic"
    TESTGENERATORADVANCED = "TESTGENERATORADVANCED", "Test Generator - Advanced"
    TESTGENERATOREXPERT = "TESTGENERATOREXPERT", "Test Generator - Expert"
    TESTEVALUATOR = "TESTEVALUATOR", "Test Evaluator"
    EXPLAINSQL = "EXPLAINSQL", "SQL Explainer"
    ASKFORHUMANHELP = "ASKFORHUMANHELP", "Human Help Requester"
    VALIDATEQUESTION = "VALIDATEQUESTION", "Question Validator"


class LLMChoices(models.TextChoices):
    OPENAI = "OPENAI", "OpenAI"
    CLAUDE = "ANTHROPIC", "Anthropic"
    CODESTRAL = "CODESTRAL", "Codestral"
    DEEPSEEK = "DEEPSEEK", "DeepSeek"
    LLAMA = "META", "LLama"
    LMSTUDIO = "LMSTUDIO", "LM Studio"
    MISTRAL = "MISTRAL", "Mistral"
    OLLAMA = "OLLAMA", "Ollama"
    OPENROUTER = "OPENROUTER", "OpenRouter"
    GEMINI = "GEMINI", "Gemini"
    GROQ = "GROQ", "Groq"


class DBMODEChoices(models.TextChoices):
    DEV = (
        "dev",
        "dev",
    )
    TEST = (
        "test",
        "test",
    )
    PROD = "prod", "prod"


class SQLDBChoices(models.TextChoices):
    MARIADB = "MariaDB", "MariaDB"
    MYSQL = "MySQL", "MySQL"
    ORACLE = "Oracle", "Oracle"
    POSTGRES = "PostgreSQL", "PostgreSQL"
    SQLSERVER = "SQLServer", "SQLServer"
    SQLITE = "SQLite", "SQLite"


class ColumnDataTypes(models.TextChoices):
    INT = "INT", "INT"
    FLOAT = "FLOAT", "FLOAT"
    DOUBLE = "DOUBLE", "DOUBLE"
    DECIMAL = "DECIMAL", "DECIMAL"
    VARCHAR = "VARCHAR", "VARCHAR"
    CHAR = "CHAR", "CHAR"
    DATE = "DATE", "DATE"
    TIME = "TIME", "TIME"
    TIMESTAMP = "TIMESTAMP", "TIMESTAMP"
    BOOLEAN = "BOOLEAN", "BOOLEAN"
    ENUM = "ENUM", "ENUM"


class VectorDbChoices(models.TextChoices):
    CHROMA = "ChromaDB", "ChromaDB"
    MILVUS = "Milvus", "Milvus"
    PGVECTOR = "PGVector", "PGVector"
    QDRANT = "Qdrant", "Qdrant"


class EmbeddingProviderChoices(models.TextChoices):
    """Choices per provider embedding esterni"""

    OPENAI = "openai", "OpenAI"
    COHERE = "cohere", "Cohere"
    MISTRAL = "mistral", "Mistral AI"
    HUGGINGFACE = "huggingface", "HuggingFace API"
    ANTHROPIC = "anthropic", "Anthropic"


class BasicAiModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    provider = models.CharField(
        max_length=100, choices=LLMChoices.choices, default=LLMChoices.CLAUDE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class AiModel(models.Model):
    basic_model = models.ForeignKey(
        BasicAiModel, on_delete=models.CASCADE, related_name="ai_models", null=True
    )
    specific_model = models.CharField(max_length=100, null=False, default="")
    name = models.CharField(max_length=100, null=True, blank=False)
    url = models.URLField(null=True, blank=True)
    temperature_allowed = models.BooleanField(default=True)
    temperature = models.DecimalField(
        help_text="""
        What sampling temperature to use, between 0 and 2. 
        Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. 
        We generally recommend altering this or top_p, not both simultaneously.
        """,
        max_digits=3,
        decimal_places=2,
        default=0.8,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        verbose_name="Temperature",
    )
    top_p = models.DecimalField(
        help_text="""
        Top-P changes how the model selects tokens for output. Tokens are selected from the most (see top-K) to least probable until the sum of their probabilities equals the top-P value. For example, if tokens A, B, and C have a probability of 0.3, 0.2, and 0.1 and the top-P value is 0.5, then the model will select either A or B as the next token by using temperature and excludes C as a candidate.
        Specify a lower value for less random responses and a higher value for more random responses.
        """,
        max_digits=3,
        decimal_places=2,
        default=0.9,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name="Top P [0.00 .. 1.00] - (0.90)",
    )
    max_tokens = models.IntegerField(
        help_text="""
        Maximum number of tokens that can be generated in the response. 
        A token is approximately four characters. 100 tokens correspond to roughly 60-80 words.
        Specify a lower value for shorter responses and a higher value for potentially longer responses.""",
        default=1280,
        validators=[MinValueValidator(128), MaxValueValidator(16000)],
        verbose_name="Max Tokens [-2 .. 16000] (128)",
    )
    timeout = models.FloatField(
        help_text="""
        Timeouts take place if this threshold, expressed in seconds, is exceeded:""",
        default=45.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(3600.0)],
        verbose_name="Timeout",
    )
    context_size = models.IntegerField(
        help_text="""
        Maximum context window size (in tokens) that the model can handle. 
        This includes both input and output tokens.""",
        default=32768,
        validators=[MinValueValidator(512), MaxValueValidator(2000000)],
        verbose_name="Context Size",
    )

    def __str__(self):
        # ritorna la concatenazione di name e specific_model
        return f"{self.name} - {self.specific_model}"


class Agent(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    agent_type = models.CharField(
        max_length=255,
        choices=AgentChoices.choices,
        default=AgentChoices.EXTRACTKEYWORDS,
    )
    ai_model = models.ForeignKey(
        AiModel, on_delete=models.CASCADE, related_name="agents", null=True
    )
    temperature = models.DecimalField(
        help_text="""
        What sampling temperature to use, between 0 and 2. 
        Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. 
        We generally recommend altering this or top_p, not both simultaneously.
        """,
        max_digits=3,
        decimal_places=2,
        default=0.8,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        verbose_name="Temperature",
    )
    top_p = models.DecimalField(
        help_text="""
        Top-P changes how the model selects tokens for output.""",
        max_digits=3,
        decimal_places=2,
        default=0.95,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    max_tokens = models.IntegerField(
        help_text="""
        The maximum number of tokens to generate.""",
        default=1280,
    )
    timeout = models.FloatField(
        help_text="""
        Timeouts take place if this threshold, expressed in seconds, is exceeded:
        """,
        default=45.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(3600.0)],
        verbose_name="Timeout",
    )
    retries = models.IntegerField(default=5)

    def __str__(self):
        return self.name


class SqlDb(models.Model):
    name = models.CharField(max_length=255)
    db_host = models.CharField(max_length=255, blank=True)
    db_type = models.CharField(
        max_length=255, choices=SQLDBChoices, default=SQLDBChoices.POSTGRES
    )
    db_name = models.CharField(max_length=255)
    db_port = models.IntegerField(blank=True, null=True)
    schema = models.CharField(max_length=255, blank=True)
    user_name = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    db_mode = models.CharField(
        max_length=255, choices=DBMODEChoices, default=DBMODEChoices.DEV
    )
    vector_db = models.OneToOneField(
        "VectorDb",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    language = models.CharField(max_length=50, blank=True, default="English")
    scope = models.TextField(blank=True, null=True)
    scope_json = models.TextField(blank=True, null=True)
    last_columns_update = models.DateTimeField(blank=True, null=True)
    erd = models.TextField(blank=True, null=True)
    directives = models.TextField(blank=True, null=True, verbose_name="Directives")
    gdpr_report = models.JSONField(blank=True, null=True)
    gdpr_scan_date = models.DateTimeField(blank=True, null=True)

    def get_collection_name(self):
        if not self.schema or self.schema == "public":
            return self.name
        return f"{self.schema}__{self.name}"

    def __str__(self):
        return f"{self.name} - {self.db_name}"


class SqlTable(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    generated_comment = models.TextField(blank=True)
    sql_db = models.ForeignKey(SqlDb, on_delete=models.CASCADE, related_name="tables")

    def __str__(self):
        return self.name


class SqlColumn(models.Model):
    original_column_name = models.CharField(max_length=255)
    column_name = models.CharField(max_length=255, blank=True)
    data_format = models.CharField(
        max_length=255, choices=ColumnDataTypes, default=ColumnDataTypes.VARCHAR
    )
    column_description = models.TextField(blank=True)
    generated_comment = models.TextField(blank=True)
    value_description = models.TextField(blank=True)
    pk_field = models.TextField(blank=True)
    fk_field = models.TextField(blank=True)
    sql_table = models.ForeignKey(
        SqlTable, on_delete=models.CASCADE, related_name="columns"
    )


class Relationship(models.Model):
    source_table = models.ForeignKey(
        SqlTable, on_delete=models.CASCADE, related_name="source_tables"
    )
    target_table = models.ForeignKey(
        SqlTable, on_delete=models.CASCADE, related_name="target_tables"
    )
    source_column = models.ForeignKey(
        SqlColumn, on_delete=models.CASCADE, related_name="source_columns"
    )
    target_column = models.ForeignKey(
        SqlColumn, on_delete=models.CASCADE, related_name="target_columns"
    )

    def __str__(self):
        return f"{self.source_table.name}.{self.source_column.original_column_name} → {self.target_table.name}.{self.target_column.original_column_name}"

    @staticmethod
    def update_pk_fk_fields():
        # Dizionario per tenere traccia delle relazioni FK
        fk_relations = {}

        # Raccogliamo tutte le relazioni
        for rel in Relationship.objects.all():
            source_col = rel.source_column
            target_col = rel.target_column

            # Aggiorniamo solo le relazioni FK
            if source_col.id not in fk_relations:
                fk_relations[source_col.id] = set()
            fk_relations[source_col.id].add(
                f"{target_col.sql_table.name}.{target_col.original_column_name}"
            )

        # Aggiorniamo solo i campi fk_field
        for col_id, references in fk_relations.items():
            col = SqlColumn.objects.get(id=col_id)
            col.fk_field = f"{', '.join(references)}"
            col.save()


class VectorDb(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Collection/Index/Database Name",
        help_text="Name used as collection name (Qdrant, ChromaDB, Milvus) or database name (PGVector)",
    )
    vect_type = models.CharField(
        max_length=255, choices=VectorDbChoices, default=VectorDbChoices.QDRANT
    )
    host = models.CharField(max_length=255, blank=True)
    port = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=500, blank=True)
    tenant = models.CharField(max_length=255, blank=True)

    # Extended plugin compatibility fields
    url = models.URLField(blank=True, help_text="Complete URL for cloud services")
    environment = models.CharField(
        max_length=255, blank=True, help_text="Optional environment identifier"
    )

    # Embedding provider configuration (REQUIRED for external embedding services)
    embedding_provider = models.CharField(
        max_length=50,
        choices=EmbeddingProviderChoices.choices,
        default=EmbeddingProviderChoices.OPENAI,
        verbose_name="Embedding Provider",
        help_text="External embedding service provider (REQUIRED)",
    )
    embedding_model = models.CharField(
        max_length=100,
        default="text-embedding-3-small",
        verbose_name="Embedding Model",
        help_text="Model name (e.g., text-embedding-3-small for OpenAI, embed-multilingual-v3.0 for Cohere)",
    )
    embedding_base_url = models.URLField(
        blank=True,
        verbose_name="Embedding Base URL",
        help_text="Custom base URL for the embedding service (optional, for custom endpoints)",
    )
    embedding_batch_size = models.PositiveIntegerField(
        default=100,
        verbose_name="Embedding Batch Size",
        help_text="Number of texts to process in a single batch (affects performance and rate limits)",
    )
    embedding_timeout = models.PositiveIntegerField(
        default=30,
        verbose_name="Embedding Timeout (seconds)",
        help_text="Request timeout for embedding API calls",
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        # Validate uniqueness based on vector database type
        errors = {}

        # Build uniqueness check based on vect_type
        if self.vect_type == VectorDbChoices.QDRANT:
            # Qdrant: unique on (host, port, name)
            existing = VectorDb.objects.filter(
                vect_type=VectorDbChoices.QDRANT,
                host=self.host or "",
                port=self.port,
                name=self.name,
            ).exclude(pk=self.pk)

            if existing.exists():
                errors["name"] = (
                    f"A Qdrant vector database with host '{self.host}', port '{self.port}', and name '{self.name}' already exists."
                )

        elif self.vect_type == VectorDbChoices.PGVECTOR:
            # PGVector: unique on (host, port, name) - name serves as database name
            existing = VectorDb.objects.filter(
                vect_type=VectorDbChoices.PGVECTOR,
                host=self.host or "",
                port=self.port,
                name=self.name,
            ).exclude(pk=self.pk)

            if existing.exists():
                errors["name"] = (
                    f"A PGVector database with host '{self.host}', port '{self.port}', and database name '{self.name}' already exists."
                )

        elif self.vect_type == VectorDbChoices.CHROMA:
            # ChromaDB: unique on (path OR host+port, name)
            if self.path:
                existing = VectorDb.objects.filter(
                    vect_type=VectorDbChoices.CHROMA, path=self.path, name=self.name
                ).exclude(pk=self.pk)
            else:
                existing = VectorDb.objects.filter(
                    vect_type=VectorDbChoices.CHROMA,
                    host=self.host or "",
                    port=self.port,
                    name=self.name,
                ).exclude(pk=self.pk)

            if existing.exists():
                connection_desc = self.path if self.path else f"{self.host}:{self.port}"
                errors["name"] = (
                    f"A ChromaDB collection '{self.name}' already exists at '{connection_desc}'."
                )

        elif self.vect_type == VectorDbChoices.MILVUS:
            # Milvus: unique on (host, port, name)
            existing = VectorDb.objects.filter(
                vect_type=VectorDbChoices.MILVUS,
                host=self.host or "",
                port=self.port,
                name=self.name,
            ).exclude(pk=self.pk)

            if existing.exists():
                errors["name"] = (
                    f"A Milvus collection with host '{self.host}', port '{self.port}', and name '{self.name}' already exists."
                )

        # Validate embedding configuration (REQUIRED)
        if not self.embedding_provider:
            errors["embedding_provider"] = "Embedding provider is required"

        # API keys should be provided via environment variables
        # The actual validation happens at runtime in vector_store_utils.py

        if not self.embedding_model or not self.embedding_model.strip():
            errors["embedding_model"] = "Embedding model name is required"

        # Validate embedding_batch_size
        if self.embedding_batch_size <= 0:
            errors["embedding_batch_size"] = (
                "Embedding batch size must be a positive number"
            )
        elif self.embedding_batch_size > 2048:  # OpenAI max limit
            errors["embedding_batch_size"] = "Embedding batch size cannot exceed 2048"

        # Validate embedding_timeout
        if self.embedding_timeout <= 0:
            errors["embedding_timeout"] = "Embedding timeout must be a positive number"
        elif self.embedding_timeout > 300:  # 5 minutes max
            errors["embedding_timeout"] = "Embedding timeout cannot exceed 300 seconds"

        # Provider-specific model validation
        if self.embedding_provider and self.embedding_model:
            valid_models = {
                EmbeddingProviderChoices.OPENAI: [
                    "text-embedding-3-small",
                    "text-embedding-3-large",
                    "text-embedding-ada-002",
                ],
                EmbeddingProviderChoices.COHERE: [
                    "embed-multilingual-v3.0",
                    "embed-english-v3.0",
                ],
                EmbeddingProviderChoices.MISTRAL: ["mistral-embed"],
                EmbeddingProviderChoices.HUGGINGFACE: [
                    # Allow any model for HuggingFace due to flexibility
                ],
                EmbeddingProviderChoices.ANTHROPIC: [
                    # To be defined when Anthropic embeddings become available
                ],
            }

            provider_models = valid_models.get(self.embedding_provider, [])
            if provider_models and self.embedding_model not in provider_models:
                errors["embedding_model"] = (
                    f"Model '{self.embedding_model}' is not valid for {self.embedding_provider}. Valid models: {', '.join(provider_models)}"
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.name} - {self.vect_type}"


class Setting(models.Model):
    name = models.CharField(max_length=255)
    theme = models.CharField(max_length=50, null=True, blank=True)

    language = models.CharField(max_length=50)
    example_rows_for_comment = models.PositiveIntegerField(
        default=5, help_text="Number of example rows to use for comment generation"
    )
    system_prompt = models.TextField(null=True, blank=True)
    comment_model = models.ForeignKey(
        AiModel,
        on_delete=models.SET_NULL,
        null=True,
        related_name="setting_comment_models",
    )

    signature_size = models.IntegerField(
        default=30, help_text="Size of the signature - LSH"
    )
    n_grams = models.IntegerField(default=3, help_text="Number of n-grams - LSH")
    threshold = models.FloatField(
        default=0.01, help_text="Threshold value for similarity comparison - LSH"
    )
    verbose = models.BooleanField(
        default=True, help_text="Enable verbose mode for LHS preprocessing"
    )
    use_value_description = models.BooleanField(
        default=True, help_text="Enable verbose mode for similarity comparison - LSH"
    )
    max_columns_before_schema_linking = models.IntegerField(
        default=30000,
        help_text="Maximum number of columns before schema linking is required",
    )
    max_context_usage_before_linking = models.IntegerField(
        default=40,
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        help_text="Maximum percentage of context window usage before schema linking is required (0-99)",
    )

    # New LSH query-time parameters for improved retrieval
    lsh_top_n = models.IntegerField(
        default=25,
        help_text="Number of top results to retrieve from LSH search (query-time parameter)",
    )
    edit_distance_threshold = models.FloatField(
        default=0.2,
        help_text="Minimum edit distance similarity for LSH results (0.0-1.0, query-time parameter)",
    )
    embedding_similarity_threshold = models.FloatField(
        default=0.4,
        help_text="Minimum embedding similarity for LSH results (0.0-1.0, query-time parameter)",
    )
    max_examples_per_column = models.IntegerField(
        default=10,
        help_text="Maximum number of example values to retain per column (query-time parameter)",
    )

    def __str__(self):
        return self.name


class Workspace(models.Model):
    class PreprocessingStatus(models.TextChoices):
        IDLE = "IDLE", "Idle"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class WorkspaceLevel(models.TextChoices):
        BASIC = "BASIC", "Basic"
        ADVANCED = "ADVANCED", "Advanced"
        EXPERT = "EXPERT", "Expert"

    name = models.CharField(max_length=100, null=False)
    level = models.CharField(
        max_length=20, choices=WorkspaceLevel.choices, default=WorkspaceLevel.BASIC
    )
    description = models.TextField(blank=True)
    users = models.ManyToManyField(User, related_name="workspaces")
    default_workspace = models.ManyToManyField(
        User, related_name="default_workspaces", blank=True
    )
    sql_db = models.ForeignKey(
        SqlDb, on_delete=models.SET_NULL, null=True, related_name="workspaces"
    )
    default_model = models.ForeignKey(
        AiModel,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_default_model",
    )
    question_validator = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_question_validator",
    )
    kw_sel_agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, related_name="workspaces_kw"
    )
    sql_basic_agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, related_name="workspaces_sql_basic"
    )
    sql_advanced_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_sql_advanced",
    )
    sql_expert_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_sql_expert",
    )
    test_gen_agent_1 = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_test_gen_1",
    )
    test_gen_agent_2 = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_test_gen_2",
    )
    test_gen_agent_3 = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_test_gen_3",
    )
    test_evaluator_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_test_evaluator",
    )
    explain_sql_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspaces_explain_sql",
    )
    ask_human_help_agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, related_name="workspaces_ask_human"
    )
    setting = models.ForeignKey(
        Setting, on_delete=models.SET_NULL, null=True, related_name="workspaces"
    )
    last_preprocess = models.DateTimeField(blank=True, null=True)
    last_evidence_load = models.DateTimeField(blank=True, null=True)
    last_sql_loaded = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    number_of_tests_to_generate = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Total number of tests to generate for a question.",
    )
    number_of_sql_to_generate = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Number of SQL queries to generate for a question.",
    )
    evaluation_threshold = models.IntegerField(
        default=90,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage of tests that a SQL must pass to be considered acceptable (0-100).",
    )

    # New fields for async preprocessing
    preprocessing_status = models.CharField(
        max_length=20,
        choices=PreprocessingStatus.choices,
        default=PreprocessingStatus.IDLE,
    )
    task_id = models.CharField(max_length=255, blank=True, null=True)
    last_preprocess_log = models.TextField(blank=True, null=True)
    preprocessing_start_time = models.DateTimeField(blank=True, null=True)
    preprocessing_end_time = models.DateTimeField(blank=True, null=True)

    # New fields for async AI comment generation
    table_comment_status = models.CharField(
        max_length=20,
        choices=PreprocessingStatus.choices,
        default=PreprocessingStatus.IDLE,
    )
    table_comment_task_id = models.CharField(max_length=255, blank=True, null=True)
    table_comment_log = models.TextField(blank=True, null=True)
    table_comment_start_time = models.DateTimeField(blank=True, null=True)
    table_comment_end_time = models.DateTimeField(blank=True, null=True)

    column_comment_status = models.CharField(
        max_length=20,
        choices=PreprocessingStatus.choices,
        default=PreprocessingStatus.IDLE,
    )
    column_comment_task_id = models.CharField(max_length=255, blank=True, null=True)
    column_comment_log = models.TextField(blank=True, null=True)
    column_comment_start_time = models.DateTimeField(blank=True, null=True)
    column_comment_end_time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name


class GroupProfile(models.Model):
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="profile"
    )
    show_sql = models.BooleanField(
        default=False, help_text="Show SQL queries to group members"
    )
    explain_generated_query = models.BooleanField(
        default=True, help_text="Explain generated SQL query to group members"
    )

    class Meta:
        verbose_name = "Group Profile"
        verbose_name_plural = "Group Profiles"

    def __str__(self):
        return f"{self.group.name} Profile"


# Signal handler to automatically create or update GroupProfile when Group is saved
@receiver(post_save, sender=Group)
def create_or_update_group_profile(sender, instance, created, **kwargs):
    # Skip if we're in the admin (the inline will handle it)
    if created and not hasattr(instance, '_from_admin'):
        # Use get_or_create to avoid duplicate creation
        GroupProfile.objects.get_or_create(group=instance)
    elif hasattr(instance, "profile") and not created:
        instance.profile.save()


class ThothLog(models.Model):
    """
    Model to log Thoth workflow executions with all intermediate and final results
    """

    username = models.CharField(max_length=150)  # Same as Django auth User.username
    workspace = models.CharField(max_length=255)  # Same as Workspace.name
    started_at = models.DateTimeField()
    terminated_at = models.DateTimeField(null=True, blank=True)
    question = models.TextField()
    db_language = models.CharField(max_length=50)  # Same as SqlDb.language
    question_language = models.CharField(max_length=50)  # Same as SqlDb.language
    translated_question = models.TextField(blank=True)
    keywords_list = models.TextField(blank=True)
    evidences = models.TextField(blank=True)
    similar_questions = models.TextField(blank=True)
    reduced_schema = models.TextField(blank=True)
    used_mschema = models.TextField(blank=True)
    generated_tests = models.TextField(
        blank=True
    )  # Simplified: [[thinking, [tests]], ...]
    evaluation_results = models.TextField(
        blank=True
    )  # New: [[thinking, [verdicts]], ...]
    evaluation_count = models.IntegerField(default=0)  # New: Number of evaluations
    pool_of_generated_sql = models.TextField(blank=True)
    generated_sql = models.TextField(blank=True)
    sql_explanation = models.TextField(blank=True)
    # New fields from thoth_ui
    directives = models.TextField(
        blank=True, default=""
    )  # Will be populated from workspace or default
    sql_generation_failure_message = models.TextField(
        blank=True, null=True
    )  # Failure message for logging
    # Schema link strategy fields
    available_context_tokens = models.IntegerField(
        null=True, blank=True
    )  # Context window size of the model
    full_schema_tokens_count = models.IntegerField(
        null=True, blank=True
    )  # Token count of full_mschema
    schema_link_strategy = models.TextField(
        blank=True, default=""
    )  # Strategy used for token management
    # New fields for schema analysis
    similar_columns = models.TextField(
        blank=True, default=""
    )  # JSON with similar columns found
    schema_with_examples = models.TextField(
        blank=True, default=""
    )  # JSON with schema and examples
    schema_from_vector_db = models.TextField(
        blank=True, default=""
    )  # Schema retrieved from vector database
    # Selection metrics including detailed test results
    selection_metrics = models.TextField(
        blank=True, default=""
    )  # JSON with selection metrics and test details
    
    # Enhanced Evaluation fields
    enhanced_evaluation_thinking = models.TextField(
        blank=True, 
        default="",
        help_text="Enhanced evaluation reasoning and analysis"
    )
    enhanced_evaluation_answers = models.JSONField(
        blank=True, 
        null=True,
        help_text="Enhanced evaluation answers as JSON array"
    )
    enhanced_evaluation_selected_sql = models.TextField(
        blank=True, 
        null=True,
        default="",
        help_text="SQL query selected by enhanced evaluation process"
    )
    
    # Test generation and evaluation status fields
    generated_tests_count = models.IntegerField(
        default=0,
        help_text="Number of tests generated"
    )
    sql_status = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="SQL execution status (e.g., passed, failed, error)"
    )
    evaluation_case = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Evaluation case category"
    )
    
    # Detailed evaluation results
    evaluation_details = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="Detailed evaluation results as JSON array"
    )
    pass_rates = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Pass rate statistics as JSON object"
    )
    selected_sql_complexity = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Complexity level of the selected SQL query"
    )
    
    # Timing fields for SQL generation
    sql_generation_start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When SQL generation started"
    )
    sql_generation_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When SQL generation ended"
    )
    sql_generation_duration_ms = models.IntegerField(
        default=0,
        help_text="SQL generation duration in milliseconds"
    )
    
    # Timing fields for test generation
    test_generation_start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When test generation started"
    )
    test_generation_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When test generation ended"
    )
    test_generation_duration_ms = models.IntegerField(
        default=0,
        help_text="Test generation duration in milliseconds"
    )
    
    # Timing fields for evaluation
    evaluation_start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When evaluation started"
    )
    evaluation_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When evaluation ended"
    )
    evaluation_duration_ms = models.IntegerField(
        default=0,
        help_text="Evaluation duration in milliseconds"
    )
    
    # Timing fields for SQL selection
    sql_selection_start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When SQL selection started"
    )
    sql_selection_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When SQL selection ended"
    )
    sql_selection_duration_ms = models.IntegerField(
        default=0,
        help_text="SQL selection duration in milliseconds"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["-started_at"]),
            models.Index(fields=["username"]),
            models.Index(fields=["workspace"]),
        ]

    def __str__(self):
        return f"{self.username} - {self.workspace} - {self.started_at}"

    @property
    def duration(self):
        """Calculate and return user-friendly duration between started_at and terminated_at."""
        if not self.terminated_at:
            return "In progress"

        delta = self.terminated_at - self.started_at
        total_seconds = int(delta.total_seconds())

        # Format the duration in a user-friendly way
        if total_seconds < 60:
            return f"{total_seconds} second{'s' if total_seconds != 1 else ''}"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if seconds > 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} second{'s' if seconds != 1 else ''}"
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = total_seconds // 3600
            remaining = total_seconds % 3600
            minutes = remaining // 60
            if minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
            return f"{hours} hour{'s' if hours != 1 else ''}"
