# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Tests for ps command functionality."""

from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from thothai_cli.core.docker_manager import DockerManager


def test_ps_compose_calls_correct_commands():
    """Test that ps for compose mode calls the correct Docker commands."""
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
        
        # Run ps
        mgr.ps(server=None, show_all=False)
        
        # Verify docker compose ps was called
        calls = mock_run.call_args_list
        call_commands = [c[0][0] for c in calls if c[0]]
        
        # Check that compose ps is in the commands
        compose_ps_found = False
        for cmd in call_commands:
            if 'docker' in cmd and 'compose' in cmd and 'ps' in cmd:
                compose_ps_found = True
                # Verify --format table is included
                assert '--format' in cmd, "ps should include --format option"
                assert 'table' in cmd, "ps should use table format"
                break
        
        assert compose_ps_found, "docker compose ps should be called"
        
    print("SUCCESS: PS compose test passed")


def test_ps_with_show_all_flag():
    """Test that ps with --all flag includes -a option."""
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'compose'}
    
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        # Run ps with show_all=True
        mgr.ps(server=None, show_all=True)
        
        calls = mock_run.call_args_list
        call_commands = [c[0][0] for c in calls if c[0]]
        
        # Check that -a flag is present
        show_all_found = False
        for cmd in call_commands:
            if 'docker' in cmd and 'compose' in cmd and 'ps' in cmd:
                if '-a' in cmd:
                    show_all_found = True
                    break
        
        assert show_all_found, "docker compose ps should include -a flag when show_all=True"
        
    print("SUCCESS: PS with --all flag test passed")


def test_ps_remote_uses_docker_context():
    """Test that remote ps uses Docker Context for remote execution."""
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
        
        # Run ps with remote server
        mgr.ps(server="user@remotehost", show_all=False)
        
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
        
    print("SUCCESS: Remote ps test passed")


def test_swarm_ps_calls_stack_ps():
    """Test that swarm ps runs docker stack ps."""
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'swarm'}
    
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        # Run swarm_ps without service filter
        mgr.swarm_ps(service=None, server=None)
        
        calls = mock_run.call_args_list
        call_commands = [c[0][0] for c in calls if c[0]]
        
        # Check that docker stack ps was called
        stack_ps_found = False
        for cmd in call_commands:
            if 'docker' in cmd and 'stack' in cmd and 'ps' in cmd:
                stack_ps_found = True
                break
        
        assert stack_ps_found, "docker stack ps should be called"
        
    print("SUCCESS: Swarm ps test passed")


def test_swarm_ps_with_service_filter():
    """Test that swarm ps with service filter runs docker service ps."""
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    mock_config.get.return_value = {'deployment_mode': 'swarm'}
    
    mgr = DockerManager(mock_config)
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        # Run swarm_ps with service filter
        mgr.swarm_ps(service='backend', server=None)
        
        calls = mock_run.call_args_list
        call_commands = [c[0][0] for c in calls if c[0]]
        
        # Check that docker service ps was called
        service_ps_found = False
        for cmd in call_commands:
            if 'docker' in cmd and 'service' in cmd and 'ps' in cmd:
                service_ps_found = True
                break
        
        assert service_ps_found, "docker service ps should be called when service is specified"
        
    print("SUCCESS: Swarm ps with service filter test passed")


if __name__ == "__main__":
    test_ps_compose_calls_correct_commands()
    test_ps_with_show_all_flag()
    test_ps_remote_uses_docker_context()
    test_swarm_ps_calls_stack_ps()
    test_swarm_ps_with_service_filter()
    print("\nAll ps tests passed!")
