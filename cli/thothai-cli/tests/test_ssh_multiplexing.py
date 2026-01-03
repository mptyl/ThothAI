from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from thothai_cli.core.docker_manager import DockerManager

def test_ssh_multiplexing():
    # Mock ConfigManager
    mock_config = MagicMock()
    mock_config.config_path = Path("/tmp/config.yml.local")
    
    # Instantiate DockerManager
    mgr = DockerManager(mock_config)
    
    # Mock subprocess.run
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        
        # Test 1: check_connection
        mgr.check_connection("user@host")
        
        # Verify call arguments
        # Should be: ssh -o ControlMaster=auto -o ControlPath=~/.ssh/thothai-%C -o ControlPersist=600 user@host echo "Connection established"
        args, _ = mock_run.call_args
        cmd = args[0]
        
        print(f"Test 1 Command: {cmd}")
        assert "ControlMaster=auto" in cmd
        assert "ControlPath=~/.ssh/thothai-%C" in cmd
        assert "ControlPersist=600" in cmd
        assert "echo \"Connection established\"" in cmd[-1]
        
        # Test 2: _run_cmd with server
        mgr._run_cmd(["ls", "-la"], server="user@host")
        
        # Verify call arguments
        # Should be: ssh -o ControlMaster=auto ... user@host ls -la
        args, _ = mock_run.call_args
        cmd = args[0]
        
        print(f"Test 2 Command: {cmd}")
        assert "ControlMaster=auto" in cmd
        assert "ControlPath=~/.ssh/thothai-%C" in cmd
        assert "ls -la" in cmd[-1]

    print("\nSUCCESS: SSH multiplexing options are correctly applied.")

if __name__ == "__main__":
    test_ssh_multiplexing()
