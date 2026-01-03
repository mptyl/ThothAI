# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Tests for prune functionality."""

from unittest.mock import MagicMock, patch, call
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from thothai_cli.core.docker_manager import DockerManager


def test_prune_compose_calls_correct_commands():
    """Test that prune for compose mode calls the correct Docker commands."""
    # Mock ConfigManager
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'compose'}
    
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        # Default return for all commands
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        # Run prune
        result = mgr.prune(server=None, remove_volumes=True, remove_images=True)
        
        # Should return True (success)
        assert result == True
        
        # Verify docker compose down was called
        calls = mock_run.call_args_list
        call_commands = [c[0][0] for c in calls if c[0]]
        
        # Check that compose down is in the commands
        compose_down_found = False
        for cmd in call_commands:
            if 'docker' in cmd and 'compose' in cmd and 'down' in cmd:
                compose_down_found = True
                break
        
        assert compose_down_found, "docker compose down should be called"
        
    print("SUCCESS: Prune compose test passed")


def test_prune_remote_uses_docker_context():
    """Test that remote prune uses Docker Context for remote execution."""
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'compose'}
    
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        # Simulate Docker Context commands working
        def run_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            
            # Docker context ls returns existing contexts
            if cmd == ['docker', 'context', 'ls', '--format', '{{.Name}}']:
                result.stdout = "default"
            
            # Docker context show returns current context
            if cmd == ['docker', 'context', 'show']:
                result.stdout = "default"
            
            return result
        
        mock_run.side_effect = run_side_effect
        
        # Run prune with remote server
        mgr.prune(server="user@remotehost", remove_volumes=False, remove_images=False)
        
        # Check that Docker Context commands were called
        calls = [c[0][0] if c[0] else c[1].get('args', []) for c in mock_run.call_args_list]
        
        # Verify context creation was attempted
        context_create_found = any(
            'docker' in str(cmd) and 'context' in str(cmd) and 'create' in str(cmd)
            for cmd in calls
        )
        
        # Verify context use was called
        context_use_found = any(
            'docker' in str(cmd) and 'context' in str(cmd) and 'use' in str(cmd)
            for cmd in calls
        )
        
        assert context_create_found or context_use_found, "Docker Context should be used for remote execution"
        
    print("SUCCESS: Remote prune test passed")


def test_swarm_prune_calls_stack_rm():
    """Test that swarm prune removes the stack."""
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'swarm'}
    
    # Mock the swarm_config.env file not existing, so we use default stack name
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        # Run swarm prune
        result = mgr.swarm_prune(server=None, remove_volumes=True, remove_images=True)
        
        assert result == True
        
        # Verify docker stack rm was called
        calls = mock_run.call_args_list
        call_commands = [c[0][0] for c in calls if c[0]]
        
        stack_rm_found = False
        for cmd in call_commands:
            if 'docker' in cmd and 'stack' in cmd and 'rm' in cmd:
                stack_rm_found = True
                break
        
        assert stack_rm_found, "docker stack rm should be called"
        
    print("SUCCESS: Swarm prune test passed")


if __name__ == "__main__":
    test_prune_compose_calls_correct_commands()
    test_prune_remote_uses_docker_context()
    test_swarm_prune_calls_stack_rm()
    print("\nAll prune tests passed!")

