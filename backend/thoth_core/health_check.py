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

"""
Health check utilities for the Thoth backend service.
Provides comprehensive health monitoring for databases, vector stores, and system resources.
"""

import os
import time
import logging
import psutil
from datetime import datetime, timezone
from typing import Dict, Any
from django.conf import settings
from django.db import connection

from thoth_core.models import SqlDb, VectorDb
from thoth_core.dbmanagement import get_db_manager

logger = logging.getLogger(__name__)

# Store application start time for uptime calculation
_start_time = time.time()


class HealthCheckStatus:
    """Health check status constants."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthChecker:
    """Main health checker class for Thoth backend services."""

    def __init__(self):
        self.checks = {}
        self.overall_status = HealthCheckStatus.HEALTHY

    def get_service_info(self) -> Dict[str, Any]:
        """Get basic service information."""
        return {
            "service": "thoth-backend",
            "version": getattr(settings, "VERSION", "1.0.0"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime": self._get_uptime(),
            "environment": {
                "debug": settings.DEBUG,
                "docker_env": os.environ.get("DOCKER_ENV", None),
                "profile": os.environ.get("PROFILE", "Unknown"),
                "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
            },
        }

    def _get_uptime(self) -> str:
        """Calculate service uptime."""
        uptime_seconds = int(time.time() - _start_time)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def check_django_database(self) -> Dict[str, Any]:
        """Check Django's default database connection."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            # Convert PosixPath to string for JSON serialization
            db_name = settings.DATABASES["default"]["NAME"]
            if hasattr(db_name, "__fspath__"):  # Check if it's a path-like object
                db_name = str(db_name)

            return {
                "status": HealthCheckStatus.HEALTHY,
                "message": "Django database connection successful",
                "details": {
                    "engine": settings.DATABASES["default"]["ENGINE"],
                    "name": db_name,
                },
            }
        except Exception as e:
            logger.error(f"Django database health check failed: {e}")
            return {
                "status": HealthCheckStatus.UNHEALTHY,
                "message": f"Django database connection failed: {str(e)}",
                "details": {"error": str(e)},
            }

    def check_sql_databases(self) -> Dict[str, Any]:
        """Check configured SQL databases connectivity."""
        sql_dbs = SqlDb.objects.all()
        if not sql_dbs.exists():
            return {
                "status": HealthCheckStatus.HEALTHY,
                "message": "No SQL databases configured",
                "count": 0,
                "databases": [],
            }

        healthy_count = 0
        total_count = sql_dbs.count()
        database_statuses = []

        for sql_db in sql_dbs:
            try:
                db_manager = get_db_manager(sql_db)
                # Use the health_check method from the adapter interface
                if hasattr(db_manager.adapter, "health_check"):
                    is_healthy = db_manager.adapter.health_check()
                else:
                    # Fallback to simple query test
                    db_manager.adapter.execute_query("SELECT 1", fetch="one")
                    is_healthy = True

                if is_healthy:
                    healthy_count += 1
                    status = HealthCheckStatus.HEALTHY
                    message = "Connection successful"
                else:
                    status = HealthCheckStatus.UNHEALTHY
                    message = "Health check failed"

                database_statuses.append(
                    {
                        "name": sql_db.name,
                        "type": sql_db.db_type,
                        "host": sql_db.db_host,
                        "status": status,
                        "message": message,
                    }
                )

            except Exception as e:
                logger.error(f"SQL database {sql_db.name} health check failed: {e}")
                database_statuses.append(
                    {
                        "name": sql_db.name,
                        "type": sql_db.db_type,
                        "host": sql_db.db_host,
                        "status": HealthCheckStatus.UNHEALTHY,
                        "message": f"Connection failed: {str(e)}",
                    }
                )

        # Determine overall status
        if healthy_count == total_count:
            overall_status = HealthCheckStatus.HEALTHY
            message = f"All {total_count} SQL databases are healthy"
        elif healthy_count > 0:
            overall_status = HealthCheckStatus.DEGRADED
            message = f"{healthy_count}/{total_count} SQL databases are healthy"
        else:
            overall_status = HealthCheckStatus.UNHEALTHY
            message = f"All {total_count} SQL databases are unhealthy"

        return {
            "status": overall_status,
            "message": message,
            "count": total_count,
            "healthy_count": healthy_count,
            "databases": database_statuses,
        }

    def check_vector_databases(self) -> Dict[str, Any]:
        """Check configured vector databases connectivity."""
        vector_dbs = VectorDb.objects.all()
        if not vector_dbs.exists():
            return {
                "status": HealthCheckStatus.HEALTHY,
                "message": "No vector databases configured",
                "count": 0,
                "databases": [],
            }

        healthy_count = 0
        total_count = vector_dbs.count()
        database_statuses = []

        for vector_db in vector_dbs:
            try:
                # For health check, we'll just verify the vector database configuration
                # without requiring workspace context
                status_msg = "Configuration valid"
                is_healthy = True

                # Basic validation of vector database configuration
                if not vector_db.name or not vector_db.vect_type:
                    is_healthy = False
                    status_msg = "Invalid configuration"

                if is_healthy:
                    healthy_count += 1
                    status = HealthCheckStatus.HEALTHY
                    message = status_msg
                else:
                    status = HealthCheckStatus.UNHEALTHY
                    message = status_msg

                database_statuses.append(
                    {
                        "name": vector_db.name,
                        "type": vector_db.vect_type,
                        "host": vector_db.host or "N/A",
                        "status": status,
                        "message": message,
                    }
                )

            except Exception as e:
                logger.error(
                    f"Vector database {vector_db.name} health check failed: {e}"
                )
                database_statuses.append(
                    {
                        "name": vector_db.name,
                        "type": vector_db.vect_type,
                        "host": vector_db.host or "N/A",
                        "status": HealthCheckStatus.UNHEALTHY,
                        "message": f"Configuration check failed: {str(e)}",
                    }
                )

        # Determine overall status
        if healthy_count == total_count:
            overall_status = HealthCheckStatus.HEALTHY
            message = f"All {total_count} vector databases have valid configurations"
        elif healthy_count > 0:
            overall_status = HealthCheckStatus.DEGRADED
            message = f"{healthy_count}/{total_count} vector databases have valid configurations"
        else:
            overall_status = HealthCheckStatus.UNHEALTHY
            message = f"All {total_count} vector databases have configuration issues"

        return {
            "status": overall_status,
            "message": message,
            "count": total_count,
            "healthy_count": healthy_count,
            "databases": database_statuses,
        }

    def check_environment_variables(self) -> Dict[str, Any]:
        """Check required environment variables."""
        required_vars = [
            "SECRET_KEY",
            "DB_ROOT_PATH",
        ]

        optional_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "MISTRAL_API_KEY",
            "DJANGO_API_KEY",
        ]

        missing_required = []
        missing_optional = []

        for var in required_vars:
            if not os.environ.get(var):
                missing_required.append(var)

        for var in optional_vars:
            if not os.environ.get(var):
                missing_optional.append(var)

        if missing_required:
            return {
                "status": HealthCheckStatus.UNHEALTHY,
                "message": f"Missing required environment variables: {', '.join(missing_required)}",
                "missing_required": missing_required,
                "missing_optional": missing_optional,
            }
        elif missing_optional:
            return {
                "status": HealthCheckStatus.DEGRADED,
                "message": f"Missing optional environment variables: {', '.join(missing_optional)}",
                "missing_required": [],
                "missing_optional": missing_optional,
            }
        else:
            return {
                "status": HealthCheckStatus.HEALTHY,
                "message": "All environment variables are present",
                "missing_required": [],
                "missing_optional": [],
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics."""
        try:
            # Memory usage
            memory = psutil.virtual_memory()

            # CPU usage (1 second sample)
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Disk usage for the application directory
            disk = psutil.disk_usage("/")

            return {
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "used": disk.used,
                    "percent": (disk.used / disk.total) * 100,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": f"Failed to get system metrics: {str(e)}"}

    def perform_health_check(self, include_metrics: bool = False) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        start_time = time.time()

        # Basic service info
        result = self.get_service_info()

        # Perform all health checks
        checks = {
            "django_database": self.check_django_database(),
            "sql_databases": self.check_sql_databases(),
            "vector_databases": self.check_vector_databases(),
            "environment": self.check_environment_variables(),
        }

        # Add system metrics if requested
        if include_metrics:
            result["metrics"] = self.get_system_metrics()

        # Determine overall status
        overall_status = HealthCheckStatus.HEALTHY
        unhealthy_checks = []
        degraded_checks = []

        for check_name, check_result in checks.items():
            if check_result["status"] == HealthCheckStatus.UNHEALTHY:
                overall_status = HealthCheckStatus.UNHEALTHY
                unhealthy_checks.append(check_name)
            elif check_result["status"] == HealthCheckStatus.DEGRADED:
                if overall_status == HealthCheckStatus.HEALTHY:
                    overall_status = HealthCheckStatus.DEGRADED
                degraded_checks.append(check_name)

        result.update(
            {
                "status": overall_status,
                "checks": checks,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
            }
        )

        if unhealthy_checks:
            result["issues"] = {
                "unhealthy": unhealthy_checks,
                "degraded": degraded_checks,
            }
        elif degraded_checks:
            result["issues"] = {"degraded": degraded_checks}

        return result
