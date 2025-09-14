# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Environment Variable Validator for SQL Generator Service

This module validates all required environment variables at startup,
handling both local development (.env.local) and Docker environments.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates environment variables for both local and Docker environments."""
    
    # Required environment variables (must be present)
    REQUIRED_VARS = [
        'DJANGO_API_KEY',           # Required for Django API communication
        'EMBEDDING_PROVIDER',       # Embedding configuration is now env-only
        'EMBEDDING_MODEL',
        'EMBEDDING_API_KEY',
    ]
    
    # Optional but recommended variables
    RECOMMENDED_VARS = [
        'LOGFIRE_TOKEN',  # For telemetry
        'OPENAI_API_KEY',  # At least one AI provider should be configured
        'ANTHROPIC_API_KEY',
        'GEMINI_API_KEY',
        'MISTRAL_API_KEY',
        'DEEPSEEK_API_KEY',
        'OPENROUTER_API_KEY',
    ]
    
    # Environment-specific port configurations
    PORT_CONFIGS = {
        'local': {
            'PORT': '8180',
            'DJANGO_PORT': '8200',
            'QDRANT_PORT': '6334',
        },
        'docker': {
            'PORT': '8020',
            'DJANGO_PORT': '8000',
            'QDRANT_PORT': '6333',
        }
    }
    
    def __init__(self):
        """Initialize the validator and detect environment."""
        self.is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
        self.environment = 'docker' if self.is_docker else 'local'
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all environment variables.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Log environment detection
        logger.info(f"Environment detected: {self.environment.upper()}")
        if self.is_docker:
            logger.info("Running in Docker container")
        else:
            logger.info("Running in local development mode")
            
        # Validate required variables
        self._validate_required_vars()
        
        # Validate recommended variables
        self._validate_recommended_vars()
        
        # Validate AI provider configuration
        self._validate_ai_providers()
        
        # Validate port configurations
        self._validate_ports()
        
        # Validate database configuration
        self._validate_database_config()
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_required_vars(self):
        """Validate required environment variables."""
        for var in self.REQUIRED_VARS:
            value = os.getenv(var)
            if not value:
                self.errors.append(f"Required environment variable '{var}' is not set")
            else:
                logger.debug(f"✓ {var} is configured")
    
    def _validate_recommended_vars(self):
        """Validate recommended environment variables."""
        for var in self.RECOMMENDED_VARS:
            value = os.getenv(var)
            if not value:
                if var == 'LOGFIRE_TOKEN':
                    self.warnings.append(f"'{var}' not set - telemetry will be disabled")
                else:
                    # AI provider keys - we'll check at least one is set later
                    pass
            else:
                logger.debug(f"✓ {var} is configured")
    
    def _validate_ai_providers(self):
        """Ensure at least one AI provider is configured."""
        ai_providers = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY', 
            'GEMINI_API_KEY',
            'MISTRAL_API_KEY',
            'DEEPSEEK_API_KEY',
            'OPENROUTER_API_KEY',
            'OLLAMA_BASE_URL',  # For local Ollama
            'LM_STUDIO_BASE_URL',  # For LM Studio
        ]
        
        configured_providers = [p for p in ai_providers if os.getenv(p)]
        
        if not configured_providers:
            self.errors.append(
                "No AI provider configured. At least one of the following must be set: " +
                ", ".join(ai_providers)
            )
        else:
            logger.info(f"AI providers configured: {', '.join(configured_providers)}")
    
    def _validate_ports(self):
        """Validate port configurations for the current environment."""
        expected_ports = self.PORT_CONFIGS[self.environment]
        
        for port_var, expected_value in expected_ports.items():
            actual_value = os.getenv(port_var)
            
            # PORT is the main service port, others are optional
            if port_var == 'PORT' and not actual_value:
                self.warnings.append(
                    f"'{port_var}' not set, will use default: {expected_value}"
                )
            elif actual_value and actual_value != expected_value:
                self.warnings.append(
                    f"'{port_var}' is set to {actual_value}, expected {expected_value} for {self.environment} environment"
                )
    
    def _validate_database_config(self):
        """Validate database-related configurations."""
        # Check for Django API endpoint
        django_url = os.getenv('DJANGO_API_URL')
        if not django_url:
            if self.is_docker:
                default_url = "http://backend:8000"
            else:
                default_url = "http://localhost:8200"
            self.warnings.append(
                f"'DJANGO_API_URL' not set, will use default: {default_url}"
            )
        
        # Check for Qdrant configuration
        qdrant_url = os.getenv('QDRANT_URL')
        if not qdrant_url:
            if self.is_docker:
                default_url = "http://thoth-qdrant:6333"
            else:
                default_url = "http://localhost:6334"
            self.warnings.append(
                f"'QDRANT_URL' not set, will use default: {default_url}"
            )
    
    def print_validation_report(self):
        """Print a formatted validation report."""
        print("\n" + "="*60)
        print(f"ENVIRONMENT VALIDATION REPORT - {self.environment.upper()}")
        print("="*60)
        
        if self.errors:
            print("\n❌ ERRORS (must be fixed):")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS (recommended to fix):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All environment variables are properly configured!")
        
        print("="*60 + "\n")


def validate_environment() -> bool:
    """
    Main function to validate environment at startup.
    
    Returns:
        True if environment is valid, False otherwise
    """
    validator = EnvironmentValidator()
    is_valid, errors, warnings = validator.validate()
    
    # Always print the report for visibility
    validator.print_validation_report()
    
    if not is_valid:
        logger.error("Environment validation failed! Please fix the errors above.")
        logger.error("Exiting...")
        return False
    
    if warnings:
        logger.warning(f"Environment validation completed with {len(warnings)} warnings")
    else:
        logger.info("Environment validation completed successfully!")
    
    return True


def get_validated_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable with validation and logging.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if not set
        
    Returns:
        The environment variable value or default
    """
    value = os.getenv(var_name, default)
    if value:
        logger.debug(f"Using {var_name}: {value[:20]}..." if len(value) > 20 else f"Using {var_name}: {value}")
    else:
        logger.debug(f"{var_name} not set, using default: {default}")
    return value


if __name__ == "__main__":
    # Allow running standalone for testing
    logging.basicConfig(level=logging.INFO)
    if not validate_environment():
        sys.exit(1)
    print("Environment validation passed!")
