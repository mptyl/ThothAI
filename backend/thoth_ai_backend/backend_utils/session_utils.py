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


def get_current_workspace(request):
    """
    Get the current workspace from the session.

    Args:
        request: The HTTP request object, which should have `current_workspace`
                 attribute set by WorkspaceMiddleware.

    Returns:
        Workspace: The current workspace object or None if not set.

    Raises:
        ValueError: If no workspace is found on the request (and it's considered mandatory here).
    """
    if hasattr(request, "current_workspace") and request.current_workspace is not None:
        return request.current_workspace
    else:
        # Depending on how strictly this function should enforce workspace presence,
        # you might raise an error or return None.
        # For now, let's raise an error if it's expected to always be there.
        raise ValueError(
            "No current_workspace found on request. Ensure WorkspaceMiddleware is active."
        )
