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

def clean_explanation_text(explanation: str) -> str:
    """
    Cleans and formats explanation text for better Markdown rendering.

    Args:
        explanation (str): Raw explanation text

    Returns:
        str: Cleaned and formatted explanation text
    """
    if not explanation:
        return "No explanation available."

    # Remove extra whitespace and normalize line breaks
    cleaned = explanation.strip()

    # Split into paragraphs and filter out empty ones
    paragraphs = [paragraph.strip() for paragraph in cleaned.split('\n') if paragraph.strip()]

    if not paragraphs:
        return "No explanation available."

    # Apply formatting rules
    formatted_paragraphs = []

    for i, paragraph in enumerate(paragraphs):
        if i == 0:
            # First paragraph: no preceding newlines
            formatted_paragraphs.append(paragraph)
        elif paragraph.startswith('**'):
            # Paragraphs starting with ** get double newline (except first)
            formatted_paragraphs.append('\n\n' + paragraph)
        elif paragraph.startswith('-'):
            # Paragraphs starting with - get single newline
            formatted_paragraphs.append('\n' + paragraph)
        else:
            # Default: double newline for regular paragraphs
            formatted_paragraphs.append('\n\n' + paragraph)

    return ''.join(formatted_paragraphs)
