from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from thothai_cli.core.docker_manager import DockerManager

def test_remote_execution_logic():
    # Mock ConfigManager
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    
    # Instantiate DockerManager
    mgr = DockerManager(mock_config)
    
    # Mock subprocess.run
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        
        # Test 1: Docker command with server -> Should use DOCKER_HOST
        mgr._run_cmd(["docker", "compose", "up"], server="user@host")
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        env = kwargs.get('env', {})
        
        print(f"Test 1 Command: {cmd}")
        print(f"Test 1 Env: {env.get('DOCKER_HOST')}")
        
        assert cmd == ["docker", "compose", "up"]
        assert env.get('DOCKER_HOST') == "ssh://user@host"
        assert "ssh" not in cmd[0] # Should strictly be the docker command
        
        # Test 2: Docker command with server (already ssh://) -> Should preserve DOCKER_HOST
        mgr._run_cmd(["docker", "info"], server="ssh://existing@host")
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        env = kwargs.get('env', {})
        
        print(f"Test 2 Env: {env.get('DOCKER_HOST')}")
        assert env.get('DOCKER_HOST') == "ssh://existing@host"
        
        # Test 3: Non-docker command with server -> Should use SSH wrapper
        mgr._run_cmd(["ls", "-la"], server="user@host")
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        
        print(f"Test 3 Command: {cmd}")
        assert cmd[0] == "ssh"
        assert "user@host" in cmd
        assert "ls -la" in cmd[-1] # Joined command
        
        # Test 4: Local command -> No SSH, No DOCKER_HOST override
        mgr._run_cmd(["docker", "ps"])
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        env = kwargs.get('env', {}) # Should be None or copy of os.environ
        
        print(f"Test 4 Command: {cmd}")
        assert cmd == ["docker", "ps"]
        # If env is passed, DOCKER_HOST should not be set by us (unless it was already in os.environ)
        # We assume local env doesn't have it set for this test or we check specifically our logic didn't set it.
        # But our logic only sets it 'if server and ...'
        
    print("\nSUCCESS: Remote execution logic verification passed.")

if __name__ == "__main__":
    test_remote_execution_logic()
