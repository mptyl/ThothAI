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

import os
import time
import logging
import requests
from typing import Optional, Tuple
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO

logger = logging.getLogger(__name__)

# Mermaid service configuration
# Using mermaid.ink public service - no local container needed
MERMAID_INK_SERVICE = "https://mermaid.ink"


class MermaidServiceError(Exception):
    """Custom exception for Mermaid service related errors"""

    pass


def check_mermaid_service_status() -> bool:
    """
    Check if mermaid.ink service is available.

    Returns:
        bool: True if service is available, False otherwise
    """
    try:
        # Test with a simple diagram to verify mermaid.ink is working
        test_url = f"{MERMAID_INK_SERVICE}/svg/Z3JhcGggVEQKICAgIEFbVGVzdF0gLS0+IEJbU2VydmljZV0="
        response = requests.get(test_url, timeout=5)  # Quick check
        return response.status_code == 200
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        logger.warning("mermaid.ink service temporarily unavailable")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking mermaid.ink service: {e}")
        return False


def ensure_mermaid_service() -> bool:
    """
    Ensure mermaid.ink service is available.
    Since mermaid.ink is a public service, we just check its availability.

    Returns:
        bool: True if service is available, False otherwise
    """
    return check_mermaid_service_status()


def convert_erd_to_vertical_flowchart(mermaid_content: str) -> str:
    """
    Convert ERD diagram to a vertical flowchart format for better vertical layout.

    Args:
        mermaid_content (str): The original Mermaid ERD content

    Returns:
        str: Converted Mermaid flowchart content with vertical layout
    """
    if not mermaid_content:
        return mermaid_content

    lines = mermaid_content.strip().split("\n")

    # Check if it's an ERD diagram
    if not any("erDiagram" in line for line in lines):
        return mermaid_content

    # Parse ERD content
    tables = {}
    relationships = []
    current_table = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("erDiagram") or line.startswith("%%"):
            continue

        # Check for relationship (contains ||, |o, o|, etc.)
        if any(
            rel in line
            for rel in [
                "||--",
                "--||",
                "||..",
                "..||",
                "}|--",
                "--{|",
                "o|--",
                "--o|",
                "}o--",
                "--o{",
            ]
        ):
            relationships.append(line)
        else:
            # It's a table definition or column
            if not any(c in line for c in [":", "{", "}"]):
                # Table name
                current_table = line
                tables[current_table] = []
            elif current_table and ":" in line:
                # Column definition
                col_parts = line.split(" ")
                if len(col_parts) >= 2:
                    col_name = (
                        col_parts[1] if col_parts[0] in ["PK", "FK"] else col_parts[0]
                    )
                    col_type = (
                        col_parts[2]
                        if col_parts[0] in ["PK", "FK"]
                        else col_parts[1]
                        if len(col_parts) > 1
                        else ""
                    )
                    tables[current_table].append(
                        (
                            col_name,
                            col_type,
                            "PK"
                            if col_parts[0] == "PK"
                            else "FK"
                            if col_parts[0] == "FK"
                            else "",
                        )
                    )

    # Analyze relationships to create a hierarchy
    table_connections = {}
    for table in tables:
        table_connections[table] = {"parents": [], "children": []}

    for rel_line in relationships:
        parts = rel_line.split()
        if len(parts) >= 3:
            table1 = parts[0]
            table2 = parts[2] if len(parts) > 2 else parts[-1]
            if table1 in table_connections and table2 in table_connections:
                table_connections[table1]["children"].append(table2)
                table_connections[table2]["parents"].append(table1)

    # Find root tables (tables with no parents)
    root_tables = [t for t in tables if not table_connections[t]["parents"]]
    if not root_tables:
        # If no clear roots, use tables with most children
        root_tables = sorted(
            tables.keys(),
            key=lambda t: len(table_connections[t]["children"]),
            reverse=True,
        )[:2]

    # Generate vertical flowchart with explicit positioning using subgraphs
    flowchart_lines = ["flowchart TD"]  # TD for Top-Down

    # Create levels with subgraphs to force vertical arrangement
    processed = set()
    level = 0
    current_level = root_tables

    # Process tables level by level
    all_levels = []
    while current_level:
        all_levels.append(current_level[:])
        next_level = []

        for table_name in current_level:
            if table_name not in processed:
                processed.add(table_name)
                for child in table_connections[table_name]["children"]:
                    if child not in processed:
                        next_level.append(child)

        current_level = next_level
        level += 1

    # Add remaining tables to last level
    remaining = [t for t in tables if t not in processed]
    if remaining:
        all_levels.append(remaining)

    # Generate nodes grouped by level with subgraphs
    for level_idx, level_tables in enumerate(all_levels):
        if level_tables:
            # Create a subgraph for each level to force vertical grouping
            flowchart_lines.append(f'    subgraph level{level_idx}[" "]')
            flowchart_lines.append(
                "        direction LR"
            )  # Within level, arrange left-to-right

            for table_name in level_tables:
                columns = tables.get(table_name, [])

                # Create table node with columns
                node_content = f"{table_name}"
                if columns:
                    # Add column details in a compact format
                    col_list = []
                    for col_name, col_type, col_attr in columns[
                        :3
                    ]:  # Show first 3 columns for compactness
                        prefix = (
                            "🔑"
                            if col_attr == "PK"
                            else "🔗"
                            if col_attr == "FK"
                            else ""
                        )
                        col_list.append(f"{prefix}{col_name}")
                    node_content = f"{table_name}|{'|'.join(col_list)}"
                    if len(columns) > 3:
                        node_content += f"|+{len(columns) - 3}"

                # Use record shape for table-like appearance
                flowchart_lines.append(f'        {table_name}["{node_content}"]')

            flowchart_lines.append("    end")

    # Add relationships with better arrow types
    for rel_line in relationships:
        parts = rel_line.split()
        if len(parts) >= 3:
            table1 = parts[0]
            table2 = parts[2] if len(parts) > 2 else parts[-1]
            # Use different arrow styles based on relationship type
            if "||--" in rel_line or "--||" in rel_line:
                flowchart_lines.append(f"    {table1} ==> {table2}")  # One-to-many
            elif "o|--" in rel_line or "--o|" in rel_line:
                flowchart_lines.append(
                    f"    {table1} --> {table2}"
                )  # Zero-or-one-to-many
            else:
                flowchart_lines.append(
                    f"    {table1} -.-> {table2}"
                )  # Other relationships

    # Add styling for better visibility
    flowchart_lines.extend(
        [
            "    classDef default fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000",
            "    classDef rootTable fill:#fff3e0,stroke:#e65100,stroke-width:3px,color:#000",
            "    classDef subgraphStyle fill:none,stroke:none",
        ]
    )

    # Apply root table style to root tables
    for root_table in root_tables:
        flowchart_lines.append(f"    class {root_table} rootTable")

    # Apply subgraph style to make level containers invisible
    for level_idx in range(len(all_levels)):
        flowchart_lines.append(f"    class level{level_idx} subgraphStyle")

    return "\n".join(flowchart_lines)


def generate_mermaid_image(
    mermaid_content: str,
    output_format: str = "svg",
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Generate an image from Mermaid diagram content using mermaid.ink service.

    Args:
        mermaid_content (str): The Mermaid diagram content
        output_format (str): Output format ('svg', 'png', 'pdf')
        width (int, optional): Output width in pixels (not used by mermaid.ink)
        height (int, optional): Output height in pixels (not used by mermaid.ink)

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (success, output_path, error_message)
    """
    if not mermaid_content or not mermaid_content.strip():
        return False, None, "Empty Mermaid content provided"

    try:
        # Use mermaid.ink service directly - it's more reliable than self-hosted containers
        import base64

        # Encode the mermaid content for URL
        encoded_diagram = base64.b64encode(mermaid_content.encode("utf-8")).decode(
            "ascii"
        )

        # Choose the appropriate endpoint based on format
        if output_format.lower() == "svg":
            url = f"{MERMAID_INK_SERVICE}/svg/{encoded_diagram}"
            file_extension = "svg"
            content_type = "image/svg+xml"
        else:  # Default to PNG for other formats
            url = f"{MERMAID_INK_SERVICE}/img/{encoded_diagram}"
            file_extension = "png"
            content_type = "image/png"

        # Make HTTP request to mermaid.ink
        response = requests.get(url, timeout=20)  # Changed from 30 to 20

        if response.status_code != 200:
            error_msg = f"mermaid.ink returned status {response.status_code}"
            if response.text:
                error_msg += f": {response.text}"
            logger.error(error_msg)
            return False, None, error_msg

        # Create temporary file to save the response
        exports_dir = os.path.join(settings.BASE_DIR, "exports")
        os.makedirs(exports_dir, exist_ok=True)

        # Save response to file
        output_filename = f"erd_{int(time.time())}.{file_extension}"
        output_path = os.path.join(exports_dir, output_filename)

        if content_type == "image/svg+xml":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)
        else:
            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info(
            f"Successfully generated Mermaid {file_extension.upper()}: {output_path}"
        )
        return True, output_path, None

    except requests.exceptions.Timeout:
        error_msg = "Diagram generation service is temporarily unavailable. Please try again later."
        logger.warning("mermaid.ink service timeout")
        return False, None, error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Diagram generation service is temporarily unavailable. Please try again later."
        logger.warning("mermaid.ink service connection error")
        return False, None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP request to mermaid.ink failed: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during Mermaid generation: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def generate_erd_pdf(
    mermaid_content: str, db_name: str
) -> Tuple[bool, Optional[HttpResponse], Optional[str]]:
    """
    Generate A4-optimized PDF from ERD Mermaid content.

    Args:
        mermaid_content (str): The Mermaid diagram content
        db_name (str): Database name for the title

    Returns:
        Tuple[bool, Optional[HttpResponse], Optional[str]]: (success, pdf_response, error_message)
    """
    if not mermaid_content or not mermaid_content.strip():
        return False, None, "No ERD diagram available"

    try:
        # Generate PNG image using the HTTP service
        success, image_path, error_msg = generate_mermaid_image(
            mermaid_content, output_format="png"
        )

        if not success:
            return False, None, error_msg or "Failed to generate ERD image"

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=0.75 * inch,
        )

        # Prepare content
        styles = getSampleStyleSheet()
        story = []

        # Title
        title = Paragraph(f"{db_name} - Entity Relationship Diagram", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 0.3 * inch))

        # Image - fit to page width while maintaining aspect ratio
        try:
            img = Image(image_path)
            img._restrictSize(doc.width, doc.height - 2 * inch)  # Leave space for title
            story.append(img)
        except Exception as e:
            logger.error(f"Error adding image to PDF: {e}")
            return False, None, f"Error creating PDF: {str(e)}"

        # Build PDF
        doc.build(story)

        # Clean up temporary image file
        try:
            os.unlink(image_path)
        except Exception:
            pass

        # Create HTTP response
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{db_name}_ERD.pdf"'

        logger.info(f"Successfully generated ERD PDF for database: {db_name}")
        return True, response, None

    except Exception as e:
        error_msg = f"Error generating ERD PDF: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def get_erd_display_image(
    mermaid_content: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Generate SVG image for web display from ERD Mermaid content.

    Args:
        mermaid_content (str): The Mermaid diagram content

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (success, image_path, error_message)
    """
    if not mermaid_content or not mermaid_content.strip():
        return False, None, "No ERD diagram available"

    return generate_mermaid_image(mermaid_content, output_format="svg")
