# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Groq adapter for PydanticAI to handle structured output limitations.

Groq models don't support native structured output via tool/function calling.
This adapter wraps Groq models to provide JSON-based structured output support.
"""

import json
import re
from typing import TypeVar, Type, Optional, Any, Dict
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class GroqStructuredAdapter:
    """
    Adapter that enables structured output for Groq models.
    
    Since Groq doesn't support native structured output, this adapter:
    1. Modifies system prompts to request JSON output
    2. Parses the JSON response into Pydantic models
    3. Provides fallback mechanisms for parsing failures
    """
    
    @staticmethod
    def create_json_agent(
        model: GroqModel,
        result_type: Type[T],
        system_prompt: str,
        **agent_kwargs
    ) -> Agent[T]:
        """
        Creates a PydanticAI agent that works with Groq's JSON output.
        
        Args:
            model: The Groq model instance
            result_type: The Pydantic model type for structured output
            system_prompt: The original system prompt
            **agent_kwargs: Additional arguments for the Agent
            
        Returns:
            An Agent configured for JSON-based structured output
        """
        
        # Get the schema from the Pydantic model
        schema = result_type.model_json_schema()
        
        # Create a detailed JSON instruction
        json_instruction = GroqStructuredAdapter._create_json_instruction(schema)
        
        # Enhance the system prompt with JSON instructions
        enhanced_prompt = f"""{system_prompt}

{json_instruction}

CRITICAL: You MUST respond with ONLY a valid JSON object. Do not include any markdown formatting, explanations, or additional text outside the JSON structure."""
        
        # Create a text-only agent since Groq can't handle structured output
        text_agent = Agent[str](
            model,
            system_prompt=enhanced_prompt,
            **agent_kwargs
        )
        
        # Wrap the agent to parse JSON responses
        return GroqStructuredAdapter._wrap_agent(text_agent, result_type)
    
    @staticmethod
    def _create_json_instruction(schema: Dict[str, Any]) -> str:
        """
        Creates detailed JSON instructions from a Pydantic schema.
        
        Args:
            schema: The JSON schema from the Pydantic model
            
        Returns:
            A formatted instruction string
        """
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        field_descriptions = []
        for field_name, field_info in properties.items():
            field_type = field_info.get('type', 'any')
            description = field_info.get('description', '')
            is_required = field_name in required
            
            field_desc = f"  - {field_name} ({field_type})"
            if description:
                field_desc += f": {description}"
            if is_required:
                field_desc += " [REQUIRED]"
            field_descriptions.append(field_desc)
        
        fields_str = "\n".join(field_descriptions)
        
        # Create an example based on the schema
        example = GroqStructuredAdapter._create_example_from_schema(properties)
        example_json = json.dumps(example, indent=2)
        
        return f"""
You MUST return your response as a valid JSON object with the following structure:

Fields:
{fields_str}

Example format:
```json
{example_json}
```

Remember: Return ONLY the JSON object, no additional text or markdown."""
    
    @staticmethod
    def _create_example_from_schema(properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates an example JSON object from schema properties.
        
        Args:
            properties: Schema properties dictionary
            
        Returns:
            Example dictionary with appropriate placeholder values
        """
        example = {}
        for field_name, field_info in properties.items():
            field_type = field_info.get('type', 'string')
            
            if field_type == 'string':
                example[field_name] = f"<{field_name}_value>"
            elif field_type == 'number':
                example[field_name] = 0.0
            elif field_type == 'integer':
                example[field_name] = 0
            elif field_type == 'boolean':
                example[field_name] = True
            elif field_type == 'array':
                example[field_name] = []
            elif field_type == 'object':
                example[field_name] = {}
            else:
                example[field_name] = f"<{field_name}>"
        
        return example
    
    @staticmethod
    def _wrap_agent(text_agent: Agent[str], result_type: Type[T]) -> Agent[T]:
        """
        Wraps a text agent to parse JSON responses into structured output.
        
        This is a conceptual wrapper - in practice, you'll need to handle
        the parsing at the point where you call the agent.
        
        Args:
            text_agent: The text-only agent
            result_type: The target Pydantic model type
            
        Returns:
            An agent that returns structured output
        """
        # Note: PydanticAI doesn't directly support wrapping agents like this
        # You'll need to handle the parsing in your agent execution code
        # This is a placeholder to show the concept
        
        logger.warning(
            "GroqStructuredAdapter: Direct agent wrapping not supported. "
            "Use parse_json_response() method after agent.run() instead."
        )
        return text_agent  # type: ignore
    
    @staticmethod
    def parse_json_response(response: str, result_type: Type[T]) -> Optional[T]:
        """
        Parses a JSON string response into a Pydantic model.
        
        Args:
            response: The string response from Groq
            result_type: The target Pydantic model type
            
        Returns:
            Parsed Pydantic model or None if parsing fails
        """
        try:
            # Clean up the response
            cleaned = GroqStructuredAdapter._clean_json_response(response)
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Create Pydantic model
            return result_type(**data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Failed to create Pydantic model: {e}")
            logger.debug(f"Parsed data: {data if 'data' in locals() else 'N/A'}")
            return None
    
    @staticmethod
    def _clean_json_response(response: str) -> str:
        """
        Cleans a response string to extract valid JSON.
        
        Args:
            response: Raw response string
            
        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        # Remove any text before the first {
        if "{" in response:
            response = response[response.index("{"):]
        
        # Remove any text after the last }
        if "}" in response:
            response = response[:response.rindex("}") + 1]
        
        return response.strip()


class GroqModelWrapper:
    """
    Wrapper for Groq models that provides structured output support.
    
    This class provides a simple interface for creating Groq agents
    with structured output capabilities.
    """
    
    def __init__(self, model_name: str, api_key: str):
        """
        Initialize the Groq model wrapper.
        
        Args:
            model_name: Name of the Groq model (e.g., 'llama-3.3-70b-versatile')
            api_key: Groq API key
        """
        self.model = GroqModel(
            model_name,
            provider=GroqProvider(api_key=api_key)
        )
        self.model_name = model_name
    
    def create_agent(
        self,
        result_type: Optional[Type[T]] = None,
        system_prompt: str = "",
        **agent_kwargs
    ) -> Agent:
        """
        Creates an agent with optional structured output support.
        
        Args:
            result_type: Optional Pydantic model for structured output
            system_prompt: System prompt for the agent
            **agent_kwargs: Additional Agent arguments
            
        Returns:
            Configured Agent instance
        """
        if result_type is None:
            # Simple text agent
            return Agent[str](
                self.model,
                system_prompt=system_prompt,
                **agent_kwargs
            )
        else:
            # Use adapter for structured output
            logger.info(f"Creating Groq agent with JSON-based structured output for {result_type.__name__}")
            return GroqStructuredAdapter.create_json_agent(
                self.model,
                result_type,
                system_prompt,
                **agent_kwargs
            )
    
    async def run_with_structured_output(
        self,
        agent: Agent[str],
        prompt: str,
        result_type: Type[T],
        **run_kwargs
    ) -> Optional[T]:
        """
        Runs an agent and parses the response as structured output.
        
        Args:
            agent: The text agent to run
            prompt: User prompt
            result_type: Pydantic model type for parsing
            **run_kwargs: Additional run arguments
            
        Returns:
            Parsed structured output or None if parsing fails
        """
        result = await agent.run(prompt, **run_kwargs)
        
        if hasattr(result, 'output') and isinstance(result.output, str):
            return GroqStructuredAdapter.parse_json_response(result.output, result_type)
        else:
            logger.error(f"Unexpected result type: {type(result)}")
            return None


# Helper function for easy integration
def create_groq_agent_with_fallback(
    model_name: str,
    api_key: str,
    result_type: Optional[Type[T]] = None,
    system_prompt: str = "",
    **agent_kwargs
) -> Agent:
    """
    Creates a Groq agent with automatic structured output handling.
    
    This is a convenience function that automatically handles the
    differences between text and structured output for Groq models.
    
    Args:
        model_name: Groq model name
        api_key: Groq API key
        result_type: Optional Pydantic model for structured output
        system_prompt: System prompt
        **agent_kwargs: Additional Agent arguments
        
    Returns:
        Configured Agent instance
    """
    wrapper = GroqModelWrapper(model_name, api_key)
    return wrapper.create_agent(result_type, system_prompt, **agent_kwargs)