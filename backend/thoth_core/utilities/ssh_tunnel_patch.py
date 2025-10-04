# Copyright 2025 Marco Pancotti
#
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
Monkey patch for thoth-dbmanager SSH tunnel to fix Python 3.13 compatibility.

This patch fixes a scoping issue in the _build_handler method that occurs due to
stricter scoping rules introduced in Python 3.13 (PEP 709).

Issue: In Python 3.13, the pattern `stop_event = stop_event` inside a class body
fails because the name on the right side cannot reference the enclosing scope variable
when the left side creates a class attribute with the same name.

Solution: Rename the local variable to avoid the name collision.

This patch should be removed once thoth-dbmanager is updated to fix this issue upstream.
"""

import logging
from typing import Any, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from thoth_dbmanager.helpers.ssh_tunnel import SSHTunnel, _ForwardHandler


def patched_build_handler(self: "SSHTunnel", transport: Any) -> type["_ForwardHandler"]:
    """
    Patched version of SSHTunnel._build_handler that works with Python 3.13.
    
    The original method had a scoping issue where:
        stop_event = self._stop_event
        class Handler:
            stop_event = stop_event  # ← This fails in Python 3.13
    
    The fix renames the local variable to avoid the collision:
        stop_evt = self._stop_event
        class Handler:
            stop_event = stop_evt  # ← This works
    """
    from thoth_dbmanager.helpers.ssh_tunnel import _ForwardHandler
    
    config = self.config
    stop_evt = self._stop_event  # ← Renamed to avoid name collision

    class Handler(_ForwardHandler):  # type: ignore[misc]
        remote_host = config.remote_host or "localhost"
        remote_port = int(config.remote_port or 0)
        ssh_transport = transport
        stop_event = stop_evt  # ← Now references the renamed variable
        select_timeout = 1.0

    return Handler


def apply_ssh_tunnel_patch() -> None:
    """
    Apply the SSH tunnel patch for Python 3.13 compatibility.
    
    This should be called early in the application initialization,
    before any SSH tunnels are created.
    """
    try:
        from thoth_dbmanager.helpers.ssh_tunnel import SSHTunnel
        
        # Check if patch is already applied
        if hasattr(SSHTunnel._build_handler, '_patched'):
            logger.debug("SSH tunnel patch already applied")
            return
        
        # Apply the patch
        SSHTunnel._build_handler = patched_build_handler  # type: ignore[method-assign]
        SSHTunnel._build_handler._patched = True  # type: ignore[attr-defined]
        
        logger.info("Applied SSH tunnel patch for Python 3.13 compatibility")
        
    except ImportError:
        logger.warning("thoth-dbmanager not installed, SSH tunnel patch not applied")
    except Exception as e:
        logger.error(f"Failed to apply SSH tunnel patch: {e}")
        raise


if __name__ == "__main__":
    # Self-test when run directly
    logging.basicConfig(level=logging.INFO)
    apply_ssh_tunnel_patch()
    
    from thoth_dbmanager.helpers.ssh_tunnel import SSHTunnel
    if hasattr(SSHTunnel._build_handler, '_patched'):
        print("✓ Patch applied and verified successfully")
    else:
        print("✗ Patch verification failed")
        exit(1)
