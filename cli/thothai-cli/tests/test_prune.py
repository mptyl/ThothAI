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


def test_prune_remote_uses_docker_host():
    """Test that remote prune uses DOCKER_HOST environment variable."""
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'compose'}
    
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        # Run prune with remote server
        mgr.prune(server="user@remotehost", remove_volumes=False, remove_images=False)
        
        # Check that DOCKER_HOST was set in environment for docker commands
        docker_host_used = False
        for call_args in mock_run.call_args_list:
            if call_args[1].get('env', {}).get('DOCKER_HOST') == 'ssh://user@remotehost':
                docker_host_used = True
                break
        
        assert docker_host_used, "DOCKER_HOST should be set for remote execution"
        
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
    test_prune_remote_uses_docker_host()
    test_swarm_prune_calls_stack_rm()
    print("\nAll prune tests passed!")
