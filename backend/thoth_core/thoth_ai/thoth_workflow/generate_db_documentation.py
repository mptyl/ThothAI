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
import re
import json
from datetime import datetime
from django.conf import settings
from django.contrib import messages

# Removed Haystack imports - using LiteLLM instead
from thoth_core.models import SqlTable, SqlColumn, Relationship, LLMChoices
from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
    setup_default_comment_llm_model,
)
from thoth_core.utilities.utils import (
    ensure_exports_directory,
    get_docker_friendly_error_message,
)
from thoth_core.utilities.shared_paths import get_export_path

# No external imports needed - using local function


def generate_scope_html(scope_json_str):
    """Generate HTML for database scope from JSON string"""
    if not scope_json_str:
        return "<p>No scope defined for this database.</p>"

    try:
        scope_data = json.loads(scope_json_str)
        html_parts = []

        for key, value in scope_data.items():
            # Make title user-friendly: capitalize and remove camelCase
            friendly_title = re.sub(
                r"([a-z])([A-Z])", r"\1 \2", key
            )  # Add space before capitals
            friendly_title = friendly_title.replace(
                "_", " "
            )  # Replace underscores with spaces
            friendly_title = friendly_title.title()  # Capitalize each word

            html_parts.append(f"<h3>{friendly_title}</h3>")
            html_parts.append(f"<p>{value}</p>")

        return "\n".join(html_parts)
    except json.JSONDecodeError:
        return f"<p>{scope_json_str}</p>"


def generate_relationships_html(db_id):
    """Generate HTML for database relationships"""
    html_parts = []

    # Get relationships
    from thoth_core.models import Relationship

    relationships = (
        Relationship.objects.filter(source_table__sql_db__id=db_id)
        .select_related(
            "source_table", "source_column", "target_table", "target_column"
        )
        .order_by("source_table__name", "source_column__original_column_name")
    )

    if relationships.exists():
        html_parts.append("<h3>Foreign Key Relationships</h3>")

        # Create relationships table
        html_parts.append('<table class="data-table">')
        html_parts.append("<thead>")
        html_parts.append("<tr>")
        html_parts.append("<th>Source Table</th>")
        html_parts.append("<th>Source Column</th>")
        html_parts.append("<th>→</th>")
        html_parts.append("<th>Target Table</th>")
        html_parts.append("<th>Target Column</th>")
        html_parts.append("</tr>")
        html_parts.append("</thead>")
        html_parts.append("<tbody>")

        for rel in relationships:
            html_parts.append("<tr>")
            html_parts.append(f"<td><strong>{rel.source_table.name}</strong></td>")
            html_parts.append(f"<td>{rel.source_column.original_column_name}</td>")
            html_parts.append('<td style="text-align: center;">→</td>')
            html_parts.append(f"<td><strong>{rel.target_table.name}</strong></td>")
            html_parts.append(f"<td>{rel.target_column.original_column_name}</td>")
            html_parts.append("</tr>")

        html_parts.append("</tbody>")
        html_parts.append("</table>")
    else:
        html_parts.append(
            "<p>No foreign key relationships defined in this database.</p>"
        )

    return "\n".join(html_parts)


def generate_tables_html(db_id):
    """Generate HTML for tables and columns documentation"""
    html_parts = []
    tables = SqlTable.objects.filter(sql_db__id=db_id).order_by("name")

    for table in tables:
        # Table header
        html_parts.append('<div class="table-section">')
        html_parts.append(f"<h3>{table.name}</h3>")

        # Table description
        if table.description or table.generated_comment:
            desc = table.description or table.generated_comment
            html_parts.append(f'<p class="table-description">{desc}</p>')

        # Columns table
        html_parts.append('<table class="data-table">')
        html_parts.append("<thead>")
        html_parts.append("<tr>")
        html_parts.append("<th>Column Name</th>")
        html_parts.append("<th>Data Type</th>")
        html_parts.append("<th>Description</th>")
        html_parts.append("<th>Value Description</th>")
        html_parts.append("<th>FK</th>")
        html_parts.append("</tr>")
        html_parts.append("</thead>")
        html_parts.append("<tbody>")

        # Get columns and sort: PK first, then others alphabetically
        columns = SqlColumn.objects.filter(sql_table=table)
        pk_columns = []
        other_columns = []

        for column in columns:
            if column.pk_field:
                pk_columns.append(column)
            else:
                other_columns.append(column)

        # Sort each group
        pk_columns.sort(key=lambda x: x.original_column_name)
        other_columns.sort(key=lambda x: x.original_column_name)

        # Combine: PK first, then others
        sorted_columns = pk_columns + other_columns

        for column in sorted_columns:
            html_parts.append("<tr>")

            # Column name with PK indicator
            col_name = column.original_column_name
            if column.pk_field:
                col_name = f"🔑 {col_name}"
            html_parts.append(f"<td>{col_name}</td>")

            # Data type
            html_parts.append(f"<td><code>{column.data_format or 'TEXT'}</code></td>")

            # Description
            desc = column.column_description or column.generated_comment or ""
            html_parts.append(f"<td>{desc}</td>")

            # Value description
            val_desc = column.value_description or ""
            html_parts.append(f"<td>{val_desc}</td>")

            # FK column with symbol
            fk_symbol = "🔗" if column.fk_field else ""
            html_parts.append(f'<td style="text-align: center;">{fk_symbol}</td>')

            html_parts.append("</tr>")

        html_parts.append("</tbody>")
        html_parts.append("</table>")
        html_parts.append("</div>")

    return "\n".join(html_parts)


def generate_schema_string_from_models(db_id):
    """Generate schema string from Django models as fallback"""
    schema_strings = []
    tables = SqlTable.objects.filter(sql_db__id=db_id)

    for table in tables:
        table_lines = []
        table_lines.append(f"CREATE TABLE {table.name} (")

        columns = SqlColumn.objects.filter(sql_table=table)
        col_lines = []
        pk_cols = []
        fk_defs = []

        for column in columns:
            # Add column description as comment
            if column.column_description or column.generated_comment:
                desc = column.column_description or column.generated_comment
                col_lines.append(f"    -- {desc}")

            data_type = column.data_format or "TEXT"
            col_lines.append(f"    {column.original_column_name} {data_type},")

            # Collect PKs
            if column.pk_field:
                pk_cols.append(column.original_column_name)

            # Collect FKs
            if column.fk_field:
                if isinstance(column.fk_field, str) and "." in column.fk_field:
                    ref_table, ref_column = column.fk_field.split(".", 1)
                    fk_defs.append(
                        f"FOREIGN KEY ({column.original_column_name}) REFERENCES {ref_table}({ref_column})"
                    )

        # Remove trailing comma from last column
        if col_lines and col_lines[-1].endswith(","):
            col_lines[-1] = col_lines[-1][:-1]

        table_lines.extend(col_lines)

        if pk_cols:
            table_lines.append(f"    ,PRIMARY KEY ({', '.join(pk_cols)})")

        for fk_def in fk_defs:
            table_lines.append(f"    ,{fk_def}")

        table_lines.append(");")
        schema_strings.append("\n".join(table_lines))
        schema_strings.append("-" * 80)

    return "\n\n".join(schema_strings).rstrip("-" * 80).rstrip("\n")


def extract_mermaid_diagram(markdown_content):
    """Extract Mermaid diagram from markdown content."""
    mermaid_pattern = r"```mermaid\s*(.*?)\s*```"
    match = re.search(mermaid_pattern, markdown_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def generate_mermaid_image(mermaid_code, output_path):
    """Generate PNG image from Mermaid diagram code using mermaid.ink service."""
    try:
        import base64
        import requests

        if not mermaid_code or not mermaid_code.strip():
            return None, "Empty Mermaid content provided"

        # Encode the mermaid content for URL
        encoded_diagram = base64.b64encode(mermaid_code.encode("utf-8")).decode("ascii")

        # Use mermaid.ink service to generate PNG
        url = f"https://mermaid.ink/img/{encoded_diagram}"

        # Make HTTP request to mermaid.ink
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            error_msg = f"mermaid.ink returned status {response.status_code}"
            if response.text:
                error_msg += f": {response.text}"
            return None, error_msg

        # Save the PNG content to the output path
        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path, None

    except requests.exceptions.RequestException as e:
        return None, f"HTTP request to mermaid.ink failed: {str(e)}"
    except Exception as e:
        return None, f"Error generating Mermaid image: {str(e)}"


def generate_simple_erd_svg(tables_data, relationships_data):
    """Generate a simple SVG ERD diagram as fallback."""
    # Calculate layout
    table_width = 200
    table_height = 30
    row_height = 25
    margin = 50
    spacing = 100

    # Position tables in a grid
    tables_per_row = max(3, int(len(tables_data) ** 0.5) + 1)
    table_positions = {}

    for i, table in enumerate(tables_data):
        row = i // tables_per_row
        col = i % tables_per_row
        x = margin + col * (table_width + spacing)
        y = margin + row * (
            table_height + spacing + row_height * min(5, len(table["columns"]))
        )
        table_positions[table["name"]] = {
            "x": x,
            "y": y,
            "width": table_width,
            "height": table_height + row_height * min(5, len(table["columns"])),
        }

    # Calculate SVG dimensions
    max_x = max([pos["x"] + pos["width"] for pos in table_positions.values()]) + margin
    max_y = max([pos["y"] + pos["height"] for pos in table_positions.values()]) + margin

    # Generate SVG
    svg_parts = [
        f'<svg width="{max_x}" height="{max_y}" xmlns="http://www.w3.org/2000/svg">'
    ]
    svg_parts.append("<style>")
    svg_parts.append(".table { fill: #f0f0f0; stroke: #333; stroke-width: 2; }")
    svg_parts.append(".table-header { fill: #4a90e2; }")
    svg_parts.append(".table-text { font-family: Arial, sans-serif; font-size: 14px; }")
    svg_parts.append(".header-text { fill: white; font-weight: bold; }")
    svg_parts.append(".column-text { fill: #333; font-size: 12px; }")
    svg_parts.append(
        ".relationship { stroke: #666; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }"
    )
    svg_parts.append("</style>")

    # Add arrowhead marker
    svg_parts.append("<defs>")
    svg_parts.append(
        '<marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">'
    )
    svg_parts.append('<polygon points="0 0, 10 3, 0 6" fill="#666" />')
    svg_parts.append("</marker>")
    svg_parts.append("</defs>")

    # Draw tables
    for table in tables_data:
        pos = table_positions[table["name"]]

        # Table container
        svg_parts.append(f'<g transform="translate({pos["x"]},{pos["y"]})">')

        # Header background
        svg_parts.append(
            f'<rect class="table-header" x="0" y="0" width="{table_width}" height="{table_height}" />'
        )

        # Table body background
        body_height = row_height * min(5, len(table["columns"]))
        svg_parts.append(
            f'<rect class="table" x="0" y="{table_height}" width="{table_width}" height="{body_height}" />'
        )

        # Table name
        svg_parts.append(
            f'<text class="table-text header-text" x="{table_width / 2}" y="20" text-anchor="middle">{table["name"]}</text>'
        )

        # Show first few columns
        for i, col in enumerate(table["columns"][:5]):
            y_pos = table_height + 20 + i * row_height
            col_text = f"{col['name']}"
            if col["is_pk"]:
                col_text = f"🔑 {col_text}"
            elif col["is_fk"]:
                col_text = f"🔗 {col_text}"
            svg_parts.append(
                f'<text class="column-text" x="10" y="{y_pos}">{col_text}</text>'
            )

        if len(table["columns"]) > 5:
            y_pos = table_height + 20 + 5 * row_height
            svg_parts.append(
                f'<text class="column-text" x="10" y="{y_pos}">... +{len(table["columns"]) - 5} more</text>'
            )

        svg_parts.append("</g>")

    # Draw relationships
    for rel in relationships_data:
        if (
            rel["source_table"] in table_positions
            and rel["target_table"] in table_positions
        ):
            source = table_positions[rel["source_table"]]
            target = table_positions[rel["target_table"]]

            # Simple line from right of source to left of target
            x1 = source["x"] + source["width"]
            y1 = source["y"] + source["height"] / 2
            x2 = target["x"]
            y2 = target["y"] + target["height"] / 2

            # Create a path with a curve
            mid_x = (x1 + x2) / 2
            svg_parts.append(
                f'<path class="relationship" d="M {x1} {y1} Q {mid_x} {y1} {mid_x} {(y1 + y2) / 2} Q {mid_x} {y2} {x2} {y2}" />'
            )

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def parse_markdown_table(table_lines):
    """Parse markdown table and convert to HTML table."""
    if len(table_lines) < 3:  # Need at least header, separator, and one data row
        return None

    # Parse header
    header_line = table_lines[0].strip()
    if not header_line.startswith("|") or not header_line.endswith("|"):
        return None

    header_cells = [cell.strip() for cell in header_line.split("|")[1:-1]]

    # Parse separator line (ignore for now, just validate it's a separator)
    separator_line = table_lines[1].strip()
    if not all(c in "|-: " for c in separator_line):
        return None

    # Parse data rows
    data_rows = []
    for line in table_lines[2:]:
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue  # Skip malformed rows
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        # Pad with empty cells if needed
        while len(cells) < len(header_cells):
            cells.append("")
        data_rows.append(cells)

    # Generate HTML table
    html_parts = ['<table class="data-table">']

    # Header
    html_parts.append("<thead>")
    html_parts.append("<tr>")
    for cell in header_cells:
        html_parts.append(f"<th>{cell}</th>")
    html_parts.append("</tr>")
    html_parts.append("</thead>")

    # Body
    html_parts.append("<tbody>")
    for row in data_rows:
        html_parts.append("<tr>")
        for i, cell in enumerate(row):
            # Handle empty cells
            cell_content = cell if cell else "&nbsp;"
            html_parts.append(f"<td>{cell_content}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody>")

    html_parts.append("</table>")
    return "\n".join(html_parts)


def generate_complete_html(db_name, scope_html, tables_html, relationships_html):
    """Generate complete HTML documentation page with search and content blocks."""

    # Build the complete content
    content_html = f"""
        <!-- Documentation Block -->
        <div class="documentation-section" id="documentation-content">
            <h1>{db_name} Database Documentation</h1>
            
            <h2>Database Scope</h2>
            <div class="scope-section">
                {scope_html}
            </div>
            
            <h2>Tables and Columns</h2>
            <div class="tables-section">
                {tables_html}
            </div>
            
            <div class="relationships-section">
                {relationships_html}
            </div>
        </div>
    """

    # Create full HTML document
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{db_name} Database Documentation</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            width: 100%;
            background-color: #f5f5f5;
        }}
        
        h1, h2, h3 {{
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        
        h1 {{
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        
        h2 {{
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            overflow-x: auto;
        }}
        
        code {{
            background-color: #f0f0f0;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        
        .sql-code {{
            background-color: #2c3e50;
            color: #ecf0f1;
        }}
        
        ul {{
            padding-left: 30px;
        }}
        
        li {{
            margin-bottom: 5px;
        }}
        
        .erd-container {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .erd-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        
        .metadata {{
            text-align: right;
            color: #666;
            font-size: 0.9em;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        
        table, .data-table {{
            border-collapse: collapse;
            width: 100%;
            margin: 25px 0;
            background-color: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
            font-size: 14px;
        }}
        
        .data-table th, .data-table td {{
            border: 1px solid #e0e6ed;
            padding: 12px 16px;
            text-align: left;
            vertical-align: top;
        }}
        
        .data-table th {{
            background: #4a90a4;
            color: white;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        .data-table tbody tr {{
            transition: background-color 0.2s ease;
        }}
        
        .data-table tbody tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .data-table tbody tr:hover {{
            background-color: #e3f2fd;
            transform: scale(1.001);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .data-table td:first-child {{
            font-weight: 600;
            color: #2c3e50;
            background-color: rgba(52, 152, 219, 0.05);
        }}
        
        .data-table tbody tr:nth-child(even) td:first-child {{
            background-color: rgba(52, 152, 219, 0.1);
        }}
        
        .data-table code {{
            background-color: #f1f3f4;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 12px;
            color: #d63384;
        }}
        
        /* Responsive table */
        @media screen and (max-width: 768px) {{
            .data-table {{
                font-size: 12px;
            }}
            
            .data-table th, .data-table td {{
                padding: 8px 10px;
            }}
        }}
        
        /* Legacy table styles for backward compatibility */
        table:not(.data-table) {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        table:not(.data-table) th, table:not(.data-table) td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        
        table:not(.data-table) th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        
        table:not(.data-table) tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        .mermaid-placeholder {{
            padding: 20px;
            background-color: #e8f4fd;
            border: 2px dashed #3498db;
            border-radius: 4px;
            text-align: center;
            color: #2980b9;
            margin: 20px 0;
        }}
        
        .documentation-section {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .table-section {{
            margin-bottom: 40px;
        }}
        
        .table-description {{
            font-style: italic;
            color: #666;
            margin-bottom: 15px;
        }}
        
        .relationships-section {{
            margin-top: 40px;
        }}
        
        .relationship-details {{
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        
        .relationship-details h4 {{
            margin-bottom: 15px;
            color: #2c3e50;
        }}
        
        .relationship-list {{
            list-style: none;
            padding-left: 0;
        }}
        
        .relationship-list li {{
            padding: 8px 0;
            border-bottom: 1px solid #e0e6ed;
        }}
        
        .relationship-list li:last-child {{
            border-bottom: none;
        }}
        
        .relationship-list strong {{
            color: #3498db;
        }}
    </style>
</head>
<body>
    <div class="content">
        {content_html}
    </div>
    <div class="metadata">
        Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} by Thoth AI
    </div>
</body>
</html>"""

    return html_template


def generate_db_documentation(modeladmin, request, queryset):
    """
    Generates comprehensive Markdown documentation for the first selected SqlDb instance using AI.
    The documentation includes database scope, Mermaid schema diagram, table descriptions, and column details.
    """
    try:
        # Check workspace
        if not hasattr(request, "current_workspace") or not request.current_workspace:
            modeladmin.message_user(
                request,
                "No active workspace found. Please select a workspace.",
                messages.ERROR,
            )
            return

        # Get settings and validate LLM configuration
        setting = request.current_workspace.setting
        if not setting or not setting.comment_model:
            modeladmin.message_user(
                request,
                "AI model for comment generation not configured in settings.",
                messages.ERROR,
            )
            return

        # Setup LLM
        llm = setup_default_comment_llm_model(setting)
        if llm is None:
            modeladmin.message_user(
                request, "Failed to set up LLM model.", messages.ERROR
            )
            return

        # Process only the first database
        if queryset.count() > 1:
            modeladmin.message_user(
                request,
                "Multiple databases selected. Processing only the first one.",
                messages.WARNING,
            )

        db = queryset.first()
        if not db:
            modeladmin.message_user(request, "No database selected.", messages.ERROR)
            return

        # Load prompt template
        template_path = os.path.join(
            settings.BASE_DIR,
            "thoth_core",
            "thoth_ai",
            "thoth_workflow",
            "prompt_templates",
            "generate_db_documentation_prompt.txt",
        )

        with open(template_path, "r") as file:
            prompt_template_text = file.read()

        # Prepare messages for LLM - only for Mermaid generation
        llm_messages = []
        if setting.comment_model.basic_model.provider != LLMChoices.GEMINI:
            llm_messages.append(
                {
                    "role": "system",
                    "content": "You are an expert in database schema design. Generate ONLY a Mermaid ERD diagram in mermaid notation.",
                }
            )

        # Prepare prompt - template is already formatted text, not needed for LiteLLM

        # Collect database information
        # Get database scope (let LLM handle formatting)
        db_scope = db.scope or "No scope defined for this database."

        # Generate schema string from Django models
        schema_string = generate_schema_string_from_models(db.id)

        # Collect table information with descriptions
        tables_data = []
        for table in SqlTable.objects.filter(sql_db=db):
            columns_data = []
            for col in SqlColumn.objects.filter(sql_table=table):
                columns_data.append(
                    {
                        "name": col.original_column_name,
                        "expanded_name": col.column_name or col.original_column_name,
                        "data_type": col.data_format,
                        "description": col.column_description
                        or col.generated_comment
                        or "",
                        "value_description": col.value_description or "",
                        "is_pk": bool(col.pk_field),
                        "is_fk": bool(col.fk_field),
                        "fk_reference": col.fk_field if col.fk_field else "",
                    }
                )

            tables_data.append(
                {
                    "name": table.name,
                    "description": table.description or table.generated_comment or "",
                    "columns": columns_data,
                }
            )

        # Collect relationships
        relationships = Relationship.objects.filter(
            source_table__sql_db=db
        ) | Relationship.objects.filter(target_table__sql_db=db)

        relationships_data = []
        for rel in relationships:
            relationships_data.append(
                {
                    "source_table": rel.source_table.name,
                    "source_column": rel.source_column.original_column_name,
                    "target_table": rel.target_table.name,
                    "target_column": rel.target_column.original_column_name,
                    "name": f"{rel.source_table.name}_{rel.target_table.name}_fk",
                }
            )

        # Generate Mermaid diagram using LLM
        try:
            # Format the prompt with variables
            prompt_variables = {
                "db_name": db.name,
                "schema_string": schema_string,
                "tables": tables_data,
                "relationships": relationships_data,
            }

            # Preprocess template (handles both {{}} syntax and Jinja2 control structures)
            from thoth_core.thoth_ai.thoth_workflow.comment_generation_utils import (
                preprocess_template,
            )

            formatted_prompt = preprocess_template(
                prompt_template_text, prompt_variables
            )

            # If template had Jinja2 control structures, it's already rendered
            # Otherwise, we need to format it
            if "{% " not in prompt_template_text:
                formatted_prompt = formatted_prompt.format(**prompt_variables)
            llm_messages.append({"role": "user", "content": formatted_prompt})

            # Generate using LLM
            output = llm.generate(llm_messages, max_tokens=3000)

            # Extract Mermaid diagram from LLM output
            mermaid_diagram = ""
            if output and hasattr(output, "content"):
                llm_response = output.content
                mermaid_diagram = extract_mermaid_diagram(llm_response) or llm_response

                # Save ERD Mermaid diagram to database field
                db.erd = mermaid_diagram
                db.save(update_fields=["erd"])

            # Generate HTML components using Python functions
            scope_html = generate_scope_html(db.scope_json)
            tables_html = generate_tables_html(db.id)
            relationships_html = generate_relationships_html(db.id)

            # Save to file
            io_dir, error_message = ensure_exports_directory()
            if error_message:
                modeladmin.message_user(
                    request, f"Export failed: {error_message}", messages.ERROR
                )
                return

            # Create database-named directory
            db_dir = get_export_path(db.name)
            try:
                os.makedirs(db_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                docker_error = get_docker_friendly_error_message(e)
                modeladmin.message_user(
                    request,
                    f"Failed to create database directory: {docker_error}",
                    messages.ERROR,
                )
                return

            # Create filenames
            base_filename = f"{db.name}_documentation"
            html_filename = f"{base_filename}.html"
            erd_filename = f"{base_filename}_erd.png"
            svg_filename = f"{base_filename}_erd.svg"

            html_filepath = os.path.join(db_dir, html_filename)
            erd_filepath = os.path.join(db_dir, erd_filename)
            svg_filepath = os.path.join(db_dir, svg_filename)

            try:
                # Generate complete HTML documentation (no ERD visualization)
                html_content = generate_complete_html(
                    db_name=db.name,
                    scope_html=scope_html,
                    tables_html=tables_html,
                    relationships_html=relationships_html,
                )

                with open(html_filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)

                # Success message
                success_msg = (
                    f"Successfully generated documentation for database '{db.name}':\n"
                )
                success_msg += f"- HTML: data_exchange/{db.name}/{html_filename}\n"
                success_msg += "- ERD Mermaid diagram saved to database field"

                modeladmin.message_user(request, success_msg, level=messages.SUCCESS)

            except (OSError, PermissionError) as e:
                docker_error = get_docker_friendly_error_message(e)
                modeladmin.message_user(
                    request,
                    f"Failed to save documentation: {docker_error}",
                    level=messages.ERROR,
                )

        except Exception as e:
            modeladmin.message_user(
                request,
                f"Error generating documentation for database '{db.name}': {str(e)}",
                level=messages.ERROR,
            )

    except FileNotFoundError:
        modeladmin.message_user(
            request, "Prompt template file not found.", level=messages.ERROR
        )
    except Exception as e:
        modeladmin.message_user(
            request, f"An unexpected error occurred: {str(e)}", level=messages.ERROR
        )


generate_db_documentation.short_description = (
    "Generate database documentation (AI assisted)"
)
