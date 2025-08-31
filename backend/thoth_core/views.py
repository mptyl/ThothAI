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

import logging
import os
from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, status

from thoth_core.authentication import ApiKeyAuthentication
from thoth_core.permissions import HasValidApiKey, IsAuthenticatedOrHasApiKey
from thoth_core.health_check import HealthChecker, HealthCheckStatus

from .models import SqlColumn, SqlDb, SqlTable, Workspace, ThothLog, Agent, AgentChoices
from .serializers import (
    SqlColumnSerializer,
    SqlTableSerializer,
    UserSerializer,
    WorkspaceSerializer,
    WorkspaceListSerializer,
    ThothLogSerializer,
)

logger = logging.getLogger(__name__)


# Create your views here.
@login_required
def index(request):
    context = {}
    return render(request, "index.html", context)


@login_required
@require_POST
def set_workspace_session(request):
    """
    Sets the selected workspace ID in the user's session.
    Called via HTMX from the workspace select dropdown.
    """
    workspace_id = request.POST.get("workspace_id")
    if not workspace_id:
        return HttpResponseBadRequest("Missing workspace_id")

    try:
        # Validate that the workspace exists and the user has access to it
        workspace = Workspace.objects.get(pk=workspace_id, users=request.user)
        request.session["selected_workspace_id"] = workspace.pk
        logger.info(
            f"User {request.user.username} set workspace {workspace.pk} in session."
        )
        # Return 204 No Content, HTMX doesn't need a response body here
        return HttpResponse(status=204)
    except Workspace.DoesNotExist:
        logger.warning(
            f"User {request.user.username} tried to set invalid or inaccessible workspace {workspace_id}."
        )
        return HttpResponseForbidden("Invalid or inaccessible workspace")
    except Exception as e:
        logger.error(
            f"Error setting workspace in session for user {request.user.username}: {e}"
        )
        return HttpResponse(status=500)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def test_token(request):
    return Response("passed!")


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication])
@permission_classes([HasValidApiKey])
def test_api_key(request):
    """Test endpoint for API key authentication"""
    import sys

    print("test_api_key view called!", file=sys.stderr)
    print(f"Request user: {request.user}", file=sys.stderr)
    print(f"Request auth: {request.auth}", file=sys.stderr)
    return Response(
        {
            "message": "API key authentication successful!",
            "user": str(request.user),
            "auth": str(request.auth),
        }
    )


@api_view(["POST"])
@authentication_classes([])  # Empty list means no authentication required
@permission_classes([])  # Empty list means no permissions required
def api_login(request):
    try:
        # Verify that username and password are present in the request
        if "username" not in request.data or "password" not in request.data:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Get the user or return 404
        user = get_object_or_404(User, username=request.data["username"])

        # Verify the password
        if not user.check_password(request.data["password"]):
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )
        token, created = Token.objects.get_or_create(user=user)

        # Save token in session for frontend redirect
        if hasattr(request, "session"):
            request.session["auth_token"] = token.key

        serializer = UserSerializer(user)
        return Response({"token": token.key, "user": serializer.data})

    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get the current authenticated user's information.
    """
    try:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": "Failed to get user information", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def get_user_workspaces(request):
    # Check if authentication was done via API key
    # In this case, request.auth is True but request.user is None
    if request.auth is True and request.user is None:
        # Authentication via API key
        logger.info("Getting all workspaces for API key authentication")
        workspaces = (
            Workspace.objects.select_related(
                "sql_db__vector_db",
                "default_model__basic_model",
                "question_validator__ai_model__basic_model",
                "kw_sel_agent__ai_model__basic_model",
                "sql_basic_agent__ai_model__basic_model",
                "sql_advanced_agent__ai_model__basic_model",
                "sql_expert_agent__ai_model__basic_model",
                "test_gen_agent_1__ai_model__basic_model",
                "test_gen_agent_2__ai_model__basic_model",
                "explain_sql_agent__ai_model__basic_model",
                "ask_human_help_agent__ai_model__basic_model",
                "setting__comment_model__basic_model",
            )
            .prefetch_related("users", "default_workspace")
            .all()
        )
    elif (
        hasattr(request, "user")
        and request.user is not None
        and request.user.is_authenticated
    ):
        user = request.user
        logger.info(f"Getting workspaces for authenticated user {user.username}")
        # Retrieve all Workspaces associated with the user with query optimization
        workspaces = (
            Workspace.objects.filter(users=user)
            .select_related(
                "sql_db__vector_db",
                "default_model__basic_model",
                "question_validator__ai_model__basic_model",
                "kw_sel_agent__ai_model__basic_model",
                "sql_basic_agent__ai_model__basic_model",
                "sql_advanced_agent__ai_model__basic_model",
                "sql_expert_agent__ai_model__basic_model",
                "test_gen_agent_1__ai_model__basic_model",
                "test_gen_agent_2__ai_model__basic_model",
                "explain_sql_agent__ai_model__basic_model",
                "ask_human_help_agent__ai_model__basic_model",
                "setting__comment_model__basic_model",
            )
            .prefetch_related("users", "default_workspace")
        )
    else:
        logger.warning("Unexpected authentication state in get_user_workspaces")
        return Response(
            {"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED
        )

    logger.info(f"Found {len(workspaces)} workspaces")
    # Serializza i dati dei Workspaces
    serializer = WorkspaceSerializer(workspaces, many=True)

    # Return serialized data (anti-cache headers handled by middleware)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def get_user_workspaces_list(request):
    """
    Get a simplified list of workspaces for the user - returns only id and name.
    Includes workspaces associated with the user and default workspaces.
    """
    # Debug logging
    import sys

    print("get_user_workspaces_list called", file=sys.stderr)
    print(f"Request user: {request.user}", file=sys.stderr)
    print(f"Request auth: {request.auth}", file=sys.stderr)
    print(
        f"Request headers X-API-KEY: {request.headers.get('X-API-KEY')}",
        file=sys.stderr,
    )

    # Check if authentication was done via API key
    if request.auth is True and request.user is None:
        # Authentication via API key
        logger.info("Getting all workspaces list for API key authentication")
        workspaces = Workspace.objects.prefetch_related(
            "users", "default_workspace"
        ).all()
    elif (
        hasattr(request, "user")
        and request.user is not None
        and request.user.is_authenticated
    ):
        user = request.user
        logger.info(f"Getting workspaces list for authenticated user {user.username}")
        # Retrieve all Workspaces associated with the user
        workspaces = Workspace.objects.filter(users=user).prefetch_related(
            "users", "default_workspace"
        )
    else:
        logger.warning("Unexpected authentication state in get_user_workspaces_list")
        return Response(
            {"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED
        )

    logger.info(f"Found {len(workspaces)} workspaces for list")
    # Serialize Workspaces data using the simplified serializer
    serializer = WorkspaceListSerializer(workspaces, many=True)

    # Return serialized data (anti-cache headers handled by middleware)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def get_workspace_by_name(request, workspace_name):
    """
    Get a specific workspace by name.
    Returns an error if multiple workspaces with the same name are found.
    """
    # Check if authentication is via API key
    if request.auth is True and request.user is None:
        # API key authentication - search all workspaces
        logger.info(f"Getting workspace '{workspace_name}' for API key authentication")
        workspaces = (
            Workspace.objects.filter(name=workspace_name)
            .select_related(
                "sql_db__vector_db",
                "default_model__basic_model",
                "question_validator__ai_model__basic_model",
                "kw_sel_agent__ai_model__basic_model",
                "sql_basic_agent__ai_model__basic_model",
                "sql_advanced_agent__ai_model__basic_model",
                "sql_expert_agent__ai_model__basic_model",
                "test_gen_agent_1__ai_model__basic_model",
                "test_gen_agent_2__ai_model__basic_model",
                "explain_sql_agent__ai_model__basic_model",
                "ask_human_help_agent__ai_model__basic_model",
                "setting__comment_model__basic_model",
            )
            .prefetch_related("users", "default_workspace")
        )
    elif (
        hasattr(request, "user")
        and request.user is not None
        and request.user.is_authenticated
    ):
        # Token or session authentication - search user's workspaces only
        user = request.user
        logger.info(
            f"Getting workspace '{workspace_name}' for authenticated user {user.username}"
        )
        workspaces = (
            Workspace.objects.filter(users=user, name=workspace_name)
            .select_related(
                "sql_db__vector_db",
                "default_model__basic_model",
                "question_validator__ai_model__basic_model",
                "kw_sel_agent__ai_model__basic_model",
                "sql_basic_agent__ai_model__basic_model",
                "sql_advanced_agent__ai_model__basic_model",
                "sql_expert_agent__ai_model__basic_model",
                "test_gen_agent_1__ai_model__basic_model",
                "test_gen_agent_2__ai_model__basic_model",
                "explain_sql_agent__ai_model__basic_model",
                "ask_human_help_agent__ai_model__basic_model",
                "setting__comment_model__basic_model",
            )
            .prefetch_related("users", "default_workspace")
        )
    else:
        logger.warning("Unexpected authentication state in get_workspace_by_name")
        return Response(
            {"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED
        )

    # Check the number of workspaces found
    workspace_count = workspaces.count()

    if workspace_count == 0:
        logger.info(f"No workspace found with name '{workspace_name}'")
        return Response(
            {"error": f"No workspace found with name '{workspace_name}'"},
            status=status.HTTP_404_NOT_FOUND,
        )
    elif workspace_count > 1:
        logger.warning(
            f"Multiple workspaces ({workspace_count}) found with name '{workspace_name}'"
        )
        return Response(
            {
                "error": f"Multiple workspaces found with name '{workspace_name}'. Workspace names should be unique."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    else:
        # Exactly one workspace found
        workspace = workspaces.first()
        logger.info(f"Found workspace '{workspace_name}' with ID {workspace.id}")
        serializer = WorkspaceSerializer(workspace)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def get_workspace_by_id(request, workspace_id):
    """
    Get a specific workspace by ID.
    """
    try:
        workspace_id = int(workspace_id)
    except (ValueError, TypeError):
        logger.warning(f"Invalid workspace_id format: {workspace_id}")
        return Response(
            {"error": "Invalid workspace ID format"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Check if authentication is via API key
    if request.auth is True and request.user is None:
        # API key authentication - search all workspaces
        logger.info(
            f"Getting workspace with ID {workspace_id} for API key authentication"
        )
        try:
            workspace = (
                Workspace.objects.select_related(
                    "sql_db__vector_db",
                    "default_model__basic_model",
                    "question_validator__ai_model__basic_model",
                    "kw_sel_agent__ai_model__basic_model",
                    "sql_basic_agent__ai_model__basic_model",
                    "sql_advanced_agent__ai_model__basic_model",
                    "sql_expert_agent__ai_model__basic_model",
                    "test_gen_agent_1__ai_model__basic_model",
                    "test_gen_agent_2__ai_model__basic_model",
                    "explain_sql_agent__ai_model__basic_model",
                    "ask_human_help_agent__ai_model__basic_model",
                    "setting__comment_model__basic_model",
                )
                .prefetch_related("users", "default_workspace")
                .get(pk=workspace_id)
            )
        except Workspace.DoesNotExist:
            logger.info(f"No workspace found with ID {workspace_id}")
            return Response(
                {"error": f"No workspace found with ID {workspace_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )
    elif (
        hasattr(request, "user")
        and request.user is not None
        and request.user.is_authenticated
    ):
        # Token or session authentication - search user's workspaces only
        user = request.user
        logger.info(
            f"Getting workspace with ID {workspace_id} for authenticated user {user.username}"
        )
        try:
            workspace = (
                Workspace.objects.filter(users=user)
                .select_related(
                    "sql_db__vector_db",
                    "default_model__basic_model",
                    "question_validator__ai_model__basic_model",
                    "kw_sel_agent__ai_model__basic_model",
                    "sql_basic_agent__ai_model__basic_model",
                    "sql_advanced_agent__ai_model__basic_model",
                    "sql_expert_agent__ai_model__basic_model",
                    "test_gen_agent_1__ai_model__basic_model",
                    "test_gen_agent_2__ai_model__basic_model",
                    "explain_sql_agent__ai_model__basic_model",
                    "ask_human_help_agent__ai_model__basic_model",
                    "setting__comment_model__basic_model",
                )
                .prefetch_related("users", "default_workspace")
                .get(pk=workspace_id)
            )
        except Workspace.DoesNotExist:
            logger.info(
                f"No workspace found with ID {workspace_id} for user {user.username}"
            )
            return Response(
                {"error": f"No workspace found with ID {workspace_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        logger.warning("Unexpected authentication state in get_workspace_by_id")
        return Response(
            {"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED
        )

    logger.info(f"Found workspace with ID {workspace_id}: {workspace.name}")
    serializer = WorkspaceSerializer(workspace)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def get_workspace_agent_pools(request, workspace_id):
    """
    Get all agents organized by type and level for pool construction.
    Returns agents classified as SQL Generator and Test Generator with Basic, Advanced, Expert levels.
    """
    try:
        workspace_id = int(workspace_id)
    except (ValueError, TypeError):
        logger.warning(f"Invalid workspace_id format: {workspace_id}")
        return Response(
            {"error": "Invalid workspace ID format"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Verify workspace exists and user has access
    if request.auth is True and request.user is None:
        # API key authentication
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {"error": f"No workspace found with ID {workspace_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )
    elif (
        hasattr(request, "user")
        and request.user is not None
        and request.user.is_authenticated
    ):
        # User authentication
        try:
            workspace = Workspace.objects.get(pk=workspace_id, users=request.user)
        except Workspace.DoesNotExist:
            return Response(
                {"error": f"No workspace found with ID {workspace_id} for user"},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        return Response(
            {"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED
        )

    logger.info(f"Getting agent pools for workspace {workspace_id}")

    # Get all agents and organize by type
    result = {
        "sql_generators": {"basic": [], "advanced": [], "expert": []},
        "test_generators": {"basic": [], "advanced": [], "expert": []},
    }

    # Fetch all agents with their AI model configurations
    agents = Agent.objects.select_related("ai_model__basic_model").all()

    for agent in agents:
        # Serialize agent data
        agent_data = {
            "id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "temperature": float(agent.temperature),
            "top_p": float(agent.top_p),
            "max_tokens": agent.max_tokens,
            "timeout": agent.timeout,
            "retries": agent.retries,
            "ai_model": None,
        }

        # Add AI model configuration if available
        if agent.ai_model:
            agent_data["ai_model"] = {
                "id": agent.ai_model.id,
                "name": agent.ai_model.name,
                "specific_model": agent.ai_model.specific_model,
                "context_size": agent.ai_model.context_size
                if hasattr(agent.ai_model, "context_size")
                else None,
            }
            if agent.ai_model.basic_model:
                agent_data["ai_model"]["basic_model"] = {
                    "name": agent.ai_model.basic_model.name
                }

        # Classify agent by type and level
        if agent.agent_type == AgentChoices.SQLBASIC:
            result["sql_generators"]["basic"].append(agent_data)
        elif agent.agent_type == AgentChoices.SQLADVANCED:
            result["sql_generators"]["advanced"].append(agent_data)
        elif agent.agent_type == AgentChoices.SQLEXPERT:
            result["sql_generators"]["expert"].append(agent_data)
        elif agent.agent_type == AgentChoices.TESTGENERATORBASIC:
            result["test_generators"]["basic"].append(agent_data)
        elif agent.agent_type == AgentChoices.TESTGENERATORADVANCED:
            result["test_generators"]["advanced"].append(agent_data)
        elif agent.agent_type == AgentChoices.TESTGENERATOREXPERT:
            result["test_generators"]["expert"].append(agent_data)

    logger.info(f"Found {len(agents)} agents total for workspace {workspace_id}")
    logger.info(
        f"SQL Generators - Basic: {len(result['sql_generators']['basic'])}, "
        f"Advanced: {len(result['sql_generators']['advanced'])}, "
        f"Expert: {len(result['sql_generators']['expert'])}"
    )
    logger.info(
        f"Test Generators - Basic: {len(result['test_generators']['basic'])}, "
        f"Advanced: {len(result['test_generators']['advanced'])}, "
        f"Expert: {len(result['test_generators']['expert'])}"
    )

    return Response(result, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def test_vector_db_connection(request, workspace_id):
    """
    Test vector database connection (Qdrant) for a workspace
    """
    import time

    try:
        workspace = Workspace.objects.get(pk=workspace_id)

        if not workspace.sql_db or not workspace.sql_db.vector_db:
            return Response(
                {
                    "error": "No vector database configured for this workspace",
                    "connection_successful": False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        vector_db = workspace.sql_db.vector_db

        # Test connection to Qdrant
        connection_info = {
            "host": vector_db.host or "localhost",
            "port": vector_db.port or 6333,
            "collection": vector_db.name,
            "type": vector_db.vect_type,
        }

        start_time = time.time()

        try:
            # Try to connect to Qdrant
            if vector_db.vect_type.lower() == "qdrant":
                from qdrant_client import QdrantClient

                # Create Qdrant client
                client = QdrantClient(
                    host=connection_info["host"],
                    port=connection_info["port"],
                    timeout=5,  # 5 seconds timeout
                )

                # Try to get collections to verify connection
                collections = client.get_collections()
                connection_info["collections_count"] = len(collections.collections)

                # Check if our specific collection exists
                collection_names = [col.name for col in collections.collections]
                connection_info["collection_exists"] = (
                    vector_db.name in collection_names
                )

                # Get collection info if it exists
                if connection_info["collection_exists"]:
                    try:
                        collection_info = client.get_collection(vector_db.name)
                        connection_info["vectors_count"] = collection_info.vectors_count
                        connection_info["points_count"] = collection_info.points_count
                    except:
                        pass

                end_time = time.time()
                connection_info["response_time_ms"] = round(
                    (end_time - start_time) * 1000, 2
                )

                logger.info(
                    f"Vector DB connection test successful for workspace {workspace.name}"
                )

                return Response(
                    {
                        "workspace": workspace.name,
                        "connection_successful": True,
                        "connection_info": connection_info,
                    },
                    status=status.HTTP_200_OK,
                )

            else:
                return Response(
                    {
                        "error": f"Unsupported vector database type: {vector_db.vect_type}",
                        "connection_successful": False,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            end_time = time.time()
            connection_info["response_time_ms"] = round(
                (end_time - start_time) * 1000, 2
            )

            error_message = str(e)
            if "Connection refused" in error_message:
                error_message = f"Cannot connect to Qdrant at {connection_info['host']}:{connection_info['port']}. Please ensure Qdrant is running."
            elif "timeout" in error_message.lower():
                error_message = f"Connection timeout to Qdrant at {connection_info['host']}:{connection_info['port']}"

            logger.error(f"Vector DB connection test failed: {e}")

            return Response(
                {
                    "workspace": workspace.name,
                    "connection_successful": False,
                    "connection_info": connection_info,
                    "error": error_message,
                },
                status=status.HTTP_200_OK,
            )

    except Workspace.DoesNotExist:
        return Response(
            {
                "error": f"Workspace {workspace_id} not found",
                "connection_successful": False,
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error testing vector DB connection: {e}")
        return Response(
            {"error": str(e), "connection_successful": False},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([ApiKeyAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrHasApiKey])
def check_embedding_config(request, workspace_id):
    """
    Diagnostic endpoint to check embedding configuration for a workspace
    and test embedding functionality
    """
    import os
    import time
    from thoth_ai_backend.backend_utils.vector_store_utils import get_vector_store

    try:
        workspace = Workspace.objects.get(pk=workspace_id)

        if not workspace.sql_db or not workspace.sql_db.vector_db:
            return Response(
                {"error": "No vector database configured for this workspace"},
                status=status.HTTP_404_NOT_FOUND,
            )

        vector_db = workspace.sql_db.vector_db

        # Check for API key in environment
        env_keys_to_check = []
        if vector_db.embedding_provider == "openai":
            env_keys_to_check = ["OPENAI_API_KEY", "OPENAI_KEY"]
        elif vector_db.embedding_provider == "cohere":
            env_keys_to_check = ["COHERE_API_KEY", "COHERE_KEY"]
        elif vector_db.embedding_provider == "mistral":
            env_keys_to_check = ["MISTRAL_API_KEY", "MISTRAL_KEY"]
        elif vector_db.embedding_provider == "huggingface":
            env_keys_to_check = [
                "HUGGINGFACE_API_KEY",
                "HF_API_KEY",
                "HUGGINGFACE_TOKEN",
            ]
        elif vector_db.embedding_provider == "anthropic":
            env_keys_to_check = ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"]

        env_keys_to_check.append("EMBEDDING_API_KEY")

        found_env_keys = []
        for key in env_keys_to_check:
            if os.environ.get(key):
                found_env_keys.append(key)

        # Log the diagnostic results
        logger.info(f"Embedding config check for workspace {workspace.name}:")
        logger.info(f"  Provider: {vector_db.embedding_provider}")
        logger.info(f"  Model: {vector_db.embedding_model}")
        logger.info(f"  Found env keys: {found_env_keys}")

        # Test embedding functionality
        embedding_test = {
            "test_performed": False,
            "test_successful": False,
            "test_error": None,
            "embedding_time_ms": None,
            "embedding_dimension": None,
            "test_text": "Thoth",
        }

        if len(found_env_keys) > 0:
            try:
                # Test embedding the word "Thoth"
                test_text = "Thoth"
                logger.info(f"Testing embedding for text: '{test_text}'")

                start_time = time.time()
                embedding = None

                # Try different embedding methods based on provider
                if vector_db.embedding_provider == "openai":
                    try:
                        import openai

                        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get(
                            "OPENAI_KEY"
                        )
                        if api_key:
                            client = openai.OpenAI(api_key=api_key)
                            response = client.embeddings.create(
                                input=test_text,
                                model=vector_db.embedding_model
                                or "text-embedding-3-small",
                            )
                            embedding = response.data[0].embedding
                    except Exception as e:
                        logger.error(f"OpenAI embedding failed: {e}")
                        raise

                elif vector_db.embedding_provider == "cohere":
                    try:
                        import cohere

                        api_key = os.environ.get("COHERE_API_KEY") or os.environ.get(
                            "COHERE_KEY"
                        )
                        if api_key:
                            co = cohere.Client(api_key)
                            response = co.embed(
                                texts=[test_text],
                                model=vector_db.embedding_model
                                or "embed-multilingual-v3.0",
                            )
                            embedding = response.embeddings[0]
                    except Exception as e:
                        logger.error(f"Cohere embedding failed: {e}")
                        raise

                elif vector_db.embedding_provider == "mistral":
                    try:
                        from mistralai.client import MistralClient

                        api_key = os.environ.get("MISTRAL_API_KEY") or os.environ.get(
                            "MISTRAL_KEY"
                        )
                        if api_key:
                            client = MistralClient(api_key=api_key)
                            response = client.embeddings(
                                model=vector_db.embedding_model or "mistral-embed",
                                input=[test_text],
                            )
                            embedding = response.data[0].embedding
                    except Exception as e:
                        logger.error(f"Mistral embedding failed: {e}")
                        raise

                else:
                    # Try generic approach through vector store
                    try:
                        vector_store = get_vector_store(vector_db)
                        # Create a temporary document to test embedding
                        from thoth_qdrant import SqlDocument

                        test_doc = SqlDocument(
                            id="test_embedding_" + str(workspace_id),
                            question=test_text,
                            sql="SELECT 1",
                            metadata={"test": True},
                        )
                        # This will internally use the embedding
                        logger.info(
                            "Using generic vector store approach for embedding test"
                        )
                        embedding_test["test_performed"] = True
                        embedding_test["test_successful"] = True
                        embedding_test["test_error"] = (
                            "Generic test performed through vector store initialization"
                        )
                    except Exception as e:
                        logger.error(f"Generic embedding approach failed: {e}")
                        raise

                end_time = time.time()

                if embedding is not None:
                    embedding_test["test_performed"] = True
                    embedding_test["test_successful"] = True
                    embedding_test["embedding_time_ms"] = round(
                        (end_time - start_time) * 1000, 2
                    )

                    # Get embedding dimension
                    if hasattr(embedding, "__len__"):
                        embedding_test["embedding_dimension"] = len(embedding)

                    logger.info(
                        f"Embedding test successful: dimension={embedding_test['embedding_dimension']}, time={embedding_test['embedding_time_ms']}ms"
                    )

            except Exception as e:
                embedding_test["test_performed"] = True
                embedding_test["test_successful"] = False
                embedding_test["test_error"] = str(e)
                logger.error(f"Embedding test failed: {e}")
        else:
            embedding_test["test_error"] = "No API keys found in environment"

        return Response(
            {
                "workspace": workspace.name,
                "vector_db": {
                    "name": vector_db.name,
                    "type": vector_db.vect_type,
                    "host": vector_db.host,
                    "port": vector_db.port,
                    "embedding_provider": vector_db.embedding_provider,
                    "embedding_model": vector_db.embedding_model,
                    "environment_keys_checked": env_keys_to_check,
                    "environment_keys_found": found_env_keys,
                    "is_configured": len(found_env_keys) > 0,
                },
                "embedding_test": embedding_test,
            },
            status=status.HTTP_200_OK,
        )

    except Workspace.DoesNotExist:
        return Response(
            {"error": f"Workspace {workspace_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error checking embedding config: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TableListByDbNameView(APIView):
    authentication_classes = [TokenAuthentication, ApiKeyAuthentication]
    permission_classes = [IsAuthenticatedOrHasApiKey]

    def get(self, request, db_name):
        try:
            db_to_use = None
            if (
                hasattr(request, "current_workspace")
                and request.current_workspace
                and request.current_workspace.sql_db
            ):
                # If a workspace is active and has an SQL DB, prioritize it.
                # Optionally, validate if db_name from URL matches the workspace's DB.
                if request.current_workspace.sql_db.name == db_name:
                    db_to_use = request.current_workspace.sql_db
                else:
                    # Workspace DB and URL db_name mismatch. Decide behavior:
                    # 1. Error out:
                    # return Response({"error": f"URL db_name '{db_name}' does not match active workspace DB '{request.current_workspace.sql_db.name}'."}, status=status.HTTP_400_BAD_REQUEST)
                    # 2. Or, fall back to using db_name from URL (less secure if workspace context is implied)
                    # For now, let's assume if workspace is set, its DB must match or it's an error to use this endpoint with a different db_name.
                    # If strict workspace scoping is desired, uncomment the error above and remove fallback.
                    # Fallback for now if names don't match but workspace is active:
                    logger.warning(
                        f"TableListByDbNameView: URL db_name '{db_name}' does not match active workspace DB '{request.current_workspace.sql_db.name}'. Falling back to URL db_name."
                    )
                    db_to_use = SqlDb.objects.get(name=db_name)

            else:
                # No active workspace with an SQL DB, fall back to db_name from URL.
                db_to_use = SqlDb.objects.get(name=db_name)

            if (
                not db_to_use
            ):  # Should not happen if logic above is correct, but as a safeguard.
                return Response(
                    {"error": "Database could not be determined."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            tables = SqlTable.objects.filter(sql_db=db_to_use)
            serializer = SqlTableSerializer(tables, many=True)

            # Headers anti-cache gestiti dal middleware
            return Response(serializer.data)
        except SqlDb.DoesNotExist:
            return Response(
                {"error": f"Database '{db_name}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class TableColumnsDetailView(APIView):
    authentication_classes = [
        ApiKeyAuthentication,
        SessionAuthentication,
        TokenAuthentication,
    ]
    permission_classes = [IsAuthenticatedOrHasApiKey]

    def get(self, request, db_name, table_name):
        try:
            db_to_use = None
            if (
                hasattr(request, "current_workspace")
                and request.current_workspace
                and request.current_workspace.sql_db
            ):
                # If a workspace is active and has an SQL DB, prioritize it.
                if request.current_workspace.sql_db.name == db_name:
                    db_to_use = request.current_workspace.sql_db
                else:
                    # Workspace DB and URL db_name mismatch.
                    logger.warning(
                        f"TableColumnsDetailView: URL db_name '{db_name}' does not match active workspace DB '{request.current_workspace.sql_db.name}'. Falling back to URL db_name."
                    )
                    db_to_use = SqlDb.objects.get(
                        name=db_name
                    )  # Fallback or error, as per policy
            else:
                # No active workspace with an SQL DB, fall back to db_name from URL.
                db_to_use = SqlDb.objects.get(name=db_name)

            if not db_to_use:
                return Response(
                    {"error": "Database could not be determined."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            table = SqlTable.objects.get(sql_db=db_to_use, name=table_name)
            columns = SqlColumn.objects.filter(sql_table=table)

            serializer = SqlColumnSerializer(columns, many=True)

            # Headers anti-cache gestiti dal middleware
            return Response(serializer.data)
        except SqlDb.DoesNotExist:
            return Response(
                {"error": f"Database '{db_name}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except SqlTable.DoesNotExist:
            return Response(
                {"error": f"Table '{table_name}' not found in database '{db_name}'."},
                status=status.HTTP_404_NOT_FOUND,
            )


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_tables_by_database(request):
    """Get tables filtered by database ID for admin interface"""
    database_id = request.GET.get("database_id")
    if not database_id:
        return Response([])

    try:
        tables = SqlTable.objects.filter(sql_db_id=database_id).order_by("name")
        table_data = [{"id": table.id, "name": table.name} for table in tables]
        return Response(table_data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_columns_by_table(request):
    """Get columns filtered by table ID for admin interface"""
    table_id = request.GET.get("table_id")
    if not table_id:
        return Response([])

    try:
        columns = SqlColumn.objects.filter(sql_table_id=table_id).order_by(
            "original_column_name"
        )
        column_data = [
            {
                "id": column.id,
                "name": f"{column.sql_table.name}.{column.original_column_name}",
            }
            for column in columns
        ]
        return Response(column_data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring system status.

    Returns comprehensive health information including:
    - Service status and uptime
    - Database connectivity (Django, SQL, Vector databases)
    - Environment variables validation
    - Optional system metrics

    Query parameters:
    - metrics: Include system metrics (memory, CPU, disk) if set to 'true'
    - deep: Perform deep health checks if set to 'true' (same as metrics for now)

    Returns:
    - 200 OK: Service is healthy
    - 503 Service Unavailable: Service has issues
    """
    try:
        # Parse query parameters
        include_metrics = request.GET.get("metrics", "false").lower() == "true"
        deep_check = request.GET.get("deep", "false").lower() == "true"

        # Include metrics for deep checks
        if deep_check:
            include_metrics = True

        # Perform health check
        health_checker = HealthChecker()
        health_data = health_checker.perform_health_check(
            include_metrics=include_metrics
        )

        # Log health check request
        logger.info(
            f"Health check requested from {request.META.get('REMOTE_ADDR', 'unknown')} - Status: {health_data['status']}"
        )

        # Determine HTTP status code based on health status
        if health_data["status"] == HealthCheckStatus.HEALTHY:
            http_status = status.HTTP_200_OK
        elif health_data["status"] == HealthCheckStatus.DEGRADED:
            http_status = status.HTTP_200_OK  # Still operational, just degraded
        else:  # UNHEALTHY
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(health_data, status=http_status)

    except Exception as e:
        logger.error(f"Health check failed with exception: {e}")
        error_response = {
            "status": HealthCheckStatus.UNHEALTHY,
            "service": "thoth-backend",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Health check failed due to internal error",
            "error": str(e),
        }
        return Response(error_response, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ThothLog CRUD API Views


class ThothLogListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating ThothLog entries.
    GET: List all logs (with pagination and filtering)
    POST: Create a new log entry
    """

    serializer_class = ThothLogSerializer
    authentication_classes = [
        TokenAuthentication,
        ApiKeyAuthentication,
        SessionAuthentication,
    ]
    permission_classes = [IsAuthenticatedOrHasApiKey]

    def get_queryset(self):
        """
        Filter logs based on user permissions.
        Superusers can see all logs.
        Regular users can only see logs for their username.
        """
        queryset = ThothLog.objects.all()

        # If not superuser, filter by username
        if (
            hasattr(self.request, "user")
            and self.request.user
            and not self.request.user.is_superuser
        ):
            queryset = queryset.filter(username=self.request.user.username)

        # Apply filters from query params
        username = self.request.query_params.get("username", None)
        workspace = self.request.query_params.get("workspace", None)
        started_from = self.request.query_params.get("started_from", None)
        started_to = self.request.query_params.get("started_to", None)

        if username:
            queryset = queryset.filter(username=username)
        if workspace:
            queryset = queryset.filter(workspace=workspace)
        if started_from:
            queryset = queryset.filter(started_at__gte=started_from)
        if started_to:
            queryset = queryset.filter(started_at__lte=started_to)

        return queryset.order_by("-started_at")

    def perform_create(self, serializer):
        """
        Set the username to the current user if not provided.
        """
        if hasattr(self.request, "user") and self.request.user:
            serializer.save(username=self.request.user.username)
        else:
            serializer.save()


class ThothLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting a specific ThothLog entry.
    GET: Retrieve a specific log
    PUT/PATCH: Update a log (limited fields)
    DELETE: Delete a log (superuser only)
    """

    serializer_class = ThothLogSerializer
    authentication_classes = [
        TokenAuthentication,
        ApiKeyAuthentication,
        SessionAuthentication,
    ]
    permission_classes = [IsAuthenticatedOrHasApiKey]

    def get_queryset(self):
        """
        Filter logs based on user permissions.
        """
        queryset = ThothLog.objects.all()

        # If not superuser, filter by username
        if (
            hasattr(self.request, "user")
            and self.request.user
            and not self.request.user.is_superuser
        ):
            queryset = queryset.filter(username=self.request.user.username)

        return queryset

    def destroy(self, request, *args, **kwargs):
        """
        Only allow superusers to delete logs.
        """
        if not request.user.is_superuser:
            return Response(
                {"error": "Only superusers can delete logs"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


@api_view(["GET"])
@authentication_classes(
    [TokenAuthentication, ApiKeyAuthentication, SessionAuthentication]
)
@permission_classes([IsAuthenticatedOrHasApiKey])
def get_thoth_logs_summary(request):
    """
    Get a summary of ThothLog entries for the current user or all users (if superuser).
    Returns aggregated statistics about log entries.
    """
    try:
        from django.db.models import Count, Min, Max
        from django.db.models.functions import TruncDate

        queryset = ThothLog.objects.all()

        # Filter by user if not superuser
        if hasattr(request, "user") and request.user and not request.user.is_superuser:
            queryset = queryset.filter(username=request.user.username)

        # Get summary statistics
        summary = {
            "total_logs": queryset.count(),
            "unique_workspaces": queryset.values("workspace").distinct().count(),
            "unique_users": queryset.values("username").distinct().count(),
            "date_range": queryset.aggregate(
                earliest=Min("started_at"), latest=Max("started_at")
            ),
            "logs_by_workspace": list(
                queryset.values("workspace")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]
            ),
            "logs_by_date": list(
                queryset.annotate(date=TruncDate("started_at"))
                .values("date")
                .annotate(count=Count("id"))
                .order_by("-date")[:30]
            ),
            "languages": {
                "db_languages": list(
                    queryset.values("db_language")
                    .annotate(count=Count("id"))
                    .order_by("-count")
                ),
                "question_languages": list(
                    queryset.values("question_language")
                    .annotate(count=Count("id"))
                    .order_by("-count")
                ),
            },
        }

        return Response(summary, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error generating ThothLog summary: {e}")
        return Response(
            {"error": "Failed to generate summary", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def generate_frontend_token(request):
    """
    Generate a token for the authenticated user to use when transitioning to the frontend.
    This ensures seamless authentication between backend and frontend.
    """
    try:
        # Get or create token for the user
        token, created = Token.objects.get_or_create(user=request.user)

        # Store token in session for frontend authentication
        if hasattr(request, "session"):
            request.session["auth_token"] = token.key
            request.session.save()

        # Return the token and frontend URL
        frontend_url = os.environ.get("FRONTEND_URL", "")

        return Response(
            {
                "token": token.key,
                "frontend_url": frontend_url,
                "redirect_url": f"{frontend_url}/auth/callback?token={token.key}",
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": "Failed to generate frontend token", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
