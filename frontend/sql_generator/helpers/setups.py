# Copyright (c) 2025 Marco Pancotti
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Setup utilities for SQL generator - MIGRATED TO CENTRALIZED EMBEDDING MANAGEMENT

This module previously contained SafeSentenceTransformer workaround for Docker issues.
Now all embedding management is delegated to thoth-qdrant with native Qdrant integration.

MIGRATION NOTES:
- SafeSentenceTransformer REMOVED (was a Docker workaround)
- build_embedding_function REMOVED (not needed with centralized management)
- All embedding operations now go through thoth_qdrant VectorStoreInterface
"""

import logging

logger = logging.getLogger(__name__)

# This file is kept for potential future setup utilities
# All embedding operations are now handled by thoth-qdrant v0.1.1+

def get_setup_info():
    """Returns information about the current setup configuration."""
    return {
        "embedding_management": "centralized",
        "library": "thoth-qdrant>=0.1.1",
        "multilingual_support": True,
        "docker_native": True,
        "workarounds": "none - removed SafeSentenceTransformer"
    }


if __name__ == "__main__":
    # Diagnostic information
    info = get_setup_info()
    logger.info(f"Setup configuration: {info}")