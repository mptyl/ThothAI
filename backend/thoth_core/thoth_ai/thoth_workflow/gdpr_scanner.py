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

import re
from datetime import datetime
from typing import Dict, List, Any
from django.utils import timezone
from thoth_core.models import SqlDb, SqlTable

# GDPR sensitive data patterns
GDPR_PATTERNS = {
    "personal_identifiers": {
        "name": {
            "patterns": [
                r"(?i)(first|last|sur|given|middle|full|maiden|nick|user)[\s_-]?name",
                r"(?i)^name$",
                r"(?i)nombre|apellido|nom|prenom",  # Spanish/French
            ],
            "sensitivity": "MEDIUM",
            "category": "Personal Identifier",
        },
        "email": {
            "patterns": [
                r"(?i)e[\s_-]?mail",
                r"(?i)email[\s_-]?address",
                r"(?i)correo|courriel",  # Spanish/French
            ],
            "sensitivity": "HIGH",
            "category": "Contact Information",
        },
        "phone": {
            "patterns": [
                r"(?i)(phone|mobile|cell|tel|fax)",
                r"(?i)number",
                r"(?i)telefono|telephone",  # Spanish/French
            ],
            "sensitivity": "MEDIUM",
            "category": "Contact Information",
        },
        "address": {
            "patterns": [
                r"(?i)address|street|city|state|zip|postal",
                r"(?i)country|region|province",
                r"(?i)direccion|adresse",  # Spanish/French
            ],
            "sensitivity": "HIGH",
            "category": "Location Data",
        },
        "identification": {
            "patterns": [
                r"(?i)(ssn|social[\s_-]?security)",
                r"(?i)passport",
                r"(?i)driver[\s_-]?license",
                r"(?i)national[\s_-]?id",
                r"(?i)tax[\s_-]?id",
                r"(?i)dni|nif|nie",  # Spanish IDs
            ],
            "sensitivity": "CRITICAL",
            "category": "Government ID",
        },
    },
    "financial_data": {
        "payment": {
            "patterns": [
                r"(?i)credit[\s_-]?card",
                r"(?i)card[\s_-]?number",
                r"(?i)cvv|cvc|ccv",
                r"(?i)expir",
                r"(?i)tarjeta|carte",  # Spanish/French
            ],
            "sensitivity": "CRITICAL",
            "category": "Financial",
        },
        "banking": {
            "patterns": [
                r"(?i)account[\s_-]?number",
                r"(?i)iban|swift|bic",
                r"(?i)routing[\s_-]?number",
                r"(?i)bank",
                r"(?i)cuenta|compte",  # Spanish/French
            ],
            "sensitivity": "CRITICAL",
            "category": "Financial",
        },
        "financial": {
            "patterns": [
                r"(?i)salary|income|wage",
                r"(?i)balance|amount",
                r"(?i)payment|transaction",
                r"(?i)salario|revenu",  # Spanish/French
            ],
            "sensitivity": "HIGH",
            "category": "Financial",
        },
    },
    "online_identifiers": {
        "network": {
            "patterns": [
                r"(?i)ip[\s_-]?address",
                r"(?i)mac[\s_-]?address",
                r"(?i)ipv[46]",
            ],
            "sensitivity": "MEDIUM",
            "category": "Online Identifier",
        },
        "device": {
            "patterns": [
                r"(?i)device[\s_-]?id",
                r"(?i)uuid|guid",
                r"(?i)imei|serial",
                r"(?i)user[\s_-]?agent",
            ],
            "sensitivity": "MEDIUM",
            "category": "Device Information",
        },
        "session": {
            "patterns": [
                r"(?i)cookie|session[\s_-]?id",
                r"(?i)token|bearer",
                r"(?i)api[\s_-]?key",
            ],
            "sensitivity": "HIGH",
            "category": "Authentication",
        },
    },
    "special_categories": {
        "health": {
            "patterns": [
                r"(?i)health|medical|diagnosis",
                r"(?i)treatment|prescription|medication",
                r"(?i)patient|doctor|hospital",
                r"(?i)disease|illness|condition",
                r"(?i)salud|sante",  # Spanish/French
            ],
            "sensitivity": "CRITICAL",
            "category": "Health Data",
        },
        "biometric": {
            "patterns": [
                r"(?i)fingerprint|biometric",
                r"(?i)face[\s_-]?id|facial",
                r"(?i)retina|iris|dna",
                r"(?i)voice[\s_-]?print",
            ],
            "sensitivity": "CRITICAL",
            "category": "Biometric Data",
        },
        "sensitive_demographics": {
            "patterns": [
                r"(?i)race|ethnic|ethnicity",
                r"(?i)religion|religious|faith",
                r"(?i)political|politics|party",
                r"(?i)sexual[\s_-]?orientation",
                r"(?i)gender[\s_-]?identity",
                r"(?i)union[\s_-]?member",
            ],
            "sensitivity": "CRITICAL",
            "category": "Special Category Data",
        },
    },
    "location_data": {
        "geographic": {
            "patterns": [
                r"(?i)latitude|longitude|coordinates",
                r"(?i)gps|location|geolocation",
                r"(?i)postal[\s_-]?code|zip[\s_-]?code",
            ],
            "sensitivity": "HIGH",
            "category": "Location Data",
        }
    },
    "employment_data": {
        "employee": {
            "patterns": [
                r"(?i)employee[\s_-]?id",
                r"(?i)staff[\s_-]?number",
                r"(?i)department|position|role",
                r"(?i)performance|review|evaluation",
            ],
            "sensitivity": "MEDIUM",
            "category": "Employment Data",
        }
    },
}


def calculate_sensitivity_score(sensitivity_level: str) -> int:
    """Convert sensitivity level to numeric score."""
    scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    return scores.get(sensitivity_level, 0)


def identify_sensitive_column(column_name: str) -> List[Dict[str, Any]]:
    """
    Identify if a column contains sensitive data based on its name.
    Returns a list of matches with their sensitivity levels and categories.
    """
    # Skip ID fields (primary keys and foreign keys)
    id_patterns = [
        r"^id$",  # Exact match for 'id'
        r"_id$",  # Ends with '_id'
        r"id$",  # Ends with 'id' (covers cases like 'userid', 'orderid')
        r"^pk_",  # Starts with 'pk_' (primary key)
        r"^fk_",  # Starts with 'fk_' (foreign key)
    ]

    # Check if column matches any ID pattern (case-insensitive)
    for pattern in id_patterns:
        if re.search(pattern, column_name, re.IGNORECASE):
            return []  # Return empty list for ID fields

    matches = []

    for category_group, patterns_dict in GDPR_PATTERNS.items():
        for pattern_type, pattern_info in patterns_dict.items():
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, column_name):
                    matches.append(
                        {
                            "pattern_type": pattern_type,
                            "category_group": category_group,
                            "sensitivity": pattern_info["sensitivity"],
                            "category": pattern_info["category"],
                            "score": calculate_sensitivity_score(
                                pattern_info["sensitivity"]
                            ),
                        }
                    )
                    break  # Only one match per pattern type

    return matches


def scan_table_for_gdpr(table: SqlTable) -> Dict[str, Any]:
    """
    Scan a table for GDPR-sensitive columns.
    Returns a dictionary with the table analysis.
    """
    sensitive_columns = []
    max_sensitivity = "NONE"
    max_score = 0

    for column in table.columns.all():
        column_matches = identify_sensitive_column(column.original_column_name)

        if column_matches:
            # Take the highest sensitivity match for this column
            highest_match = max(column_matches, key=lambda x: x["score"])

            sensitive_columns.append(
                {
                    "column_name": column.original_column_name,
                    "data_type": column.data_format,
                    "sensitivity": highest_match["sensitivity"],
                    "category": highest_match["category"],
                    "pattern_type": highest_match["pattern_type"],
                    "description": column.column_description
                    or column.generated_comment
                    or "",
                }
            )

            # Update max sensitivity for the table
            if highest_match["score"] > max_score:
                max_score = highest_match["score"]
                max_sensitivity = highest_match["sensitivity"]

    return {
        "table_name": table.name,
        "description": table.description or table.generated_comment or "",
        "sensitive_columns": sensitive_columns,
        "column_count": table.columns.count(),
        "sensitive_column_count": len(sensitive_columns),
        "max_sensitivity": max_sensitivity,
        "has_sensitive_data": len(sensitive_columns) > 0,
    }


def scan_database_for_gdpr(db_id: int) -> Dict[str, Any]:
    """
    Perform a complete GDPR scan on a database.
    Returns a comprehensive report with all findings.
    """
    try:
        db = SqlDb.objects.get(id=db_id)
        tables = SqlTable.objects.filter(sql_db=db).prefetch_related("columns")

        # Initialize report structure
        report = {
            "database_name": db.name,
            "scan_date": timezone.now().isoformat(),
            "summary": {
                "total_tables": tables.count(),
                "tables_with_sensitive_data": 0,
                "total_columns": 0,
                "sensitive_columns": 0,
                "critical_findings": 0,
                "high_findings": 0,
                "medium_findings": 0,
                "low_findings": 0,
            },
            "categories": {},
            "tables": [],
            "recommendations": [],
        }

        # Initialize category counters
        for category_group in GDPR_PATTERNS.keys():
            report["categories"][category_group] = {"count": 0, "columns": []}

        # Scan each table
        for table in tables:
            table_analysis = scan_table_for_gdpr(table)
            report["tables"].append(table_analysis)

            # Update summary statistics
            report["summary"]["total_columns"] += table_analysis["column_count"]

            if table_analysis["has_sensitive_data"]:
                report["summary"]["tables_with_sensitive_data"] += 1
                report["summary"]["sensitive_columns"] += table_analysis[
                    "sensitive_column_count"
                ]

                # Count findings by sensitivity
                for column in table_analysis["sensitive_columns"]:
                    sensitivity = column["sensitivity"]
                    if sensitivity == "CRITICAL":
                        report["summary"]["critical_findings"] += 1
                    elif sensitivity == "HIGH":
                        report["summary"]["high_findings"] += 1
                    elif sensitivity == "MEDIUM":
                        report["summary"]["medium_findings"] += 1
                    elif sensitivity == "LOW":
                        report["summary"]["low_findings"] += 1

                    # Update category statistics
                    for category_group, patterns_dict in GDPR_PATTERNS.items():
                        for pattern_type, pattern_info in patterns_dict.items():
                            if column["pattern_type"] == pattern_type:
                                report["categories"][category_group]["count"] += 1
                                report["categories"][category_group]["columns"].append(
                                    {
                                        "table": table.name,
                                        "column": column["column_name"],
                                        "sensitivity": column["sensitivity"],
                                    }
                                )
                                break

        # Generate recommendations based on findings
        report["recommendations"] = generate_recommendations(report)

        # Calculate overall risk score
        report["risk_score"] = calculate_risk_score(report)

        return report

    except SqlDb.DoesNotExist:
        return {"error": "Database not found"}
    except Exception as e:
        return {"error": str(e)}


def generate_recommendations(report: Dict[str, Any]) -> List[str]:
    """
    Generate GDPR compliance recommendations based on scan results.
    """
    recommendations = []

    # Critical findings recommendations
    if report["summary"]["critical_findings"] > 0:
        recommendations.append(
            {
                "priority": "CRITICAL",
                "title": "Encrypt Critical Data",
                "description": f"Found {report['summary']['critical_findings']} critical sensitive data columns. Implement encryption at rest and in transit immediately.",
            }
        )
        recommendations.append(
            {
                "priority": "CRITICAL",
                "title": "Implement Access Controls",
                "description": "Restrict access to critical data columns using role-based access control (RBAC).",
            }
        )

    # High sensitivity recommendations
    if report["summary"]["high_findings"] > 0:
        recommendations.append(
            {
                "priority": "HIGH",
                "title": "Data Minimization",
                "description": f"Review {report['summary']['high_findings']} high-sensitivity columns for data minimization opportunities.",
            }
        )
        recommendations.append(
            {
                "priority": "HIGH",
                "title": "Audit Logging",
                "description": "Implement comprehensive audit logging for all access to high-sensitivity data.",
            }
        )

    # Health data specific
    if report["categories"].get("special_categories", {}).get("count", 0) > 0:
        recommendations.append(
            {
                "priority": "CRITICAL",
                "title": "Special Category Data Protection",
                "description": "Special category data (health, biometric, etc.) requires explicit consent and additional safeguards under GDPR Article 9.",
            }
        )

    # Financial data specific
    if report["categories"].get("financial_data", {}).get("count", 0) > 0:
        recommendations.append(
            {
                "priority": "CRITICAL",
                "title": "PCI DSS Compliance",
                "description": "Financial data requires PCI DSS compliance in addition to GDPR. Implement tokenization for payment card data.",
            }
        )

    # General recommendations
    if report["summary"]["sensitive_columns"] > 0:
        recommendations.append(
            {
                "priority": "MEDIUM",
                "title": "Data Retention Policy",
                "description": "Implement automated data retention and deletion policies for personal data.",
            }
        )
        recommendations.append(
            {
                "priority": "MEDIUM",
                "title": "Pseudonymization",
                "description": "Consider pseudonymization techniques for personal identifiers where possible.",
            }
        )
        recommendations.append(
            {
                "priority": "LOW",
                "title": "Privacy by Design",
                "description": "Review database schema for privacy by design principles and minimize data collection.",
            }
        )

    return recommendations


def calculate_risk_score(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate an overall risk score for GDPR compliance.
    """
    # Weighted scoring
    score = (
        report["summary"]["critical_findings"] * 10
        + report["summary"]["high_findings"] * 5
        + report["summary"]["medium_findings"] * 2
        + report["summary"]["low_findings"] * 1
    )

    # Normalize to 0-100 scale
    max_possible = report["summary"]["total_columns"] * 10
    if max_possible > 0:
        normalized_score = min(100, (score / max_possible) * 100)
    else:
        normalized_score = 0

    # Determine risk level
    if normalized_score >= 75:
        risk_level = "CRITICAL"
        risk_color = "#e74c3c"  # Deep red-orange
    elif normalized_score >= 50:
        risk_level = "HIGH"
        risk_color = "#e67e22"  # Coral/orange
    elif normalized_score >= 25:
        risk_level = "MEDIUM"
        risk_color = "#f39c12"  # Warm amber/gold
    else:
        risk_level = "LOW"
        risk_color = "#17a2b8"  # Teal/turquoise

    return {
        "score": round(normalized_score, 2),
        "level": risk_level,
        "color": risk_color,
        "description": f"Risk score: {round(normalized_score, 2)}/100 - {risk_level}",
    }


def generate_gdpr_html(report: Dict[str, Any]) -> str:
    """
    Generate HTML content for GDPR compliance scan (without full HTML document wrapper).
    """
    risk_info = report.get("risk_score", {})

    # Start with just the content, no DOCTYPE or html/head/body tags
    html = f"""
    <style>
        .gdpr-header {{
            background: #4a90a4;
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .gdpr-header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .gdpr-header h2 {{
            margin: 0 0 10px 0;
            font-size: 1.5em;
            opacity: 0.95;
        }}
        .gdpr-header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .risk-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            background-color: #fef5e7;
            color: {risk_info.get("color", "#17a2b8")};
            border: 2px solid #f39c12;
            margin-top: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid #e0e6ed;
        }}
        .summary-card h3 {{
            margin-top: 0;
            color: #4a90a4;
            font-size: 1.2em;
            margin-bottom: 15px;
        }}
        .summary-card p {{
            margin: 8px 0;
            font-size: 14px;
        }}
        .summary-card strong {{
            color: #2c3e50;
        }}
        .critical {{ color: #e74c3c; font-weight: bold; }}
        .high {{ color: #e67e22; font-weight: bold; }}
        .medium {{ color: #f39c12; }}
        .low {{ color: #17a2b8; }}
        .gdpr-table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 20px 0;
            border-collapse: collapse;
        }}
        .gdpr-table th {{
            background: #4a90a4;
            color: white;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .gdpr-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid #e0e6ed;
            font-size: 14px;
        }}
        .gdpr-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .gdpr-table tr:last-child td {{
            border-bottom: none;
        }}
        .recommendation {{
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .recommendation.critical {{ border-color: #e74c3c; }}
        .recommendation.high {{ border-color: #e67e22; }}
        .recommendation.medium {{ border-color: #f39c12; }}
        .recommendation.low {{ border-color: #17a2b8; }}
        .recommendation h4 {{
            margin-top: 0;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .category-section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid #e0e6ed;
        }}
        .category-section h3 {{
            margin-top: 0;
            color: #4a90a4;
            font-size: 1.3em;
            margin-bottom: 15px;
        }}
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .no-data h2 {{
            color: #17a2b8;
            margin-bottom: 15px;
        }}
        .no-data p {{
            color: #6c757d;
            font-size: 16px;
            line-height: 1.6;
        }}
    </style>
    
    <div class="gdpr-header">
        <h1>GDPR Compliance Report</h1>
        <h2>{report["database_name"]}</h2>
        <p>Scan Date: {report["scan_date"]}</p>
        <span class="risk-badge">{risk_info.get("description", "Risk Assessment Pending")}</span>
    </div>
    
    <div class="summary-grid">
        <div class="summary-card">
            <h3>Database Overview</h3>
            <p><strong>Total Tables:</strong> {report["summary"]["total_tables"]}</p>
            <p><strong>Total Columns:</strong> {report["summary"]["total_columns"]}</p>
        </div>
        <div class="summary-card">
            <h3>Sensitive Data Found</h3>
            <p><strong>Tables with Sensitive Data:</strong> {report["summary"]["tables_with_sensitive_data"]}</p>
            <p><strong>Sensitive Columns:</strong> {report["summary"]["sensitive_columns"]}</p>
        </div>
        <div class="summary-card">
            <h3>Findings by Severity</h3>
            <p class="critical">Critical: {report["summary"]["critical_findings"]}</p>
            <p class="high">High: {report["summary"]["high_findings"]}</p>
            <p class="medium">Medium: {report["summary"]["medium_findings"]}</p>
            <p class="low">Low: {report["summary"]["low_findings"]}</p>
        </div>
    </div>
    """

    # Add detailed findings if any sensitive data found
    if report["summary"]["sensitive_columns"] > 0:
        html += """
    <h2 style="color: #2c3e50; margin-top: 30px; margin-bottom: 15px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">Detailed Findings</h2>
    <table class="gdpr-table">
        <thead>
            <tr>
                <th>Table</th>
                <th>Column</th>
                <th>Description</th>
                <th>Data Type</th>
                <th>Category</th>
                <th>Sensitivity</th>
            </tr>
        </thead>
        <tbody>
        """

        for table in report["tables"]:
            if table["has_sensitive_data"]:
                for column in table["sensitive_columns"]:
                    sensitivity_class = column["sensitivity"].lower()
                    column_description = column.get("description", "")
                    # Format column name with description if available
                    column_display = f"{column['column_name']}"
                    if column_description:
                        description_display = column_description
                    else:
                        description_display = "<em style='color: #999;'>No description</em>"
                    
                    html += f"""
            <tr>
                <td><strong>{table["table_name"]}</strong></td>
                <td>{column_display}</td>
                <td>{description_display}</td>
                <td><code>{column["data_type"]}</code></td>
                <td>{column["category"]}</td>
                <td class="{sensitivity_class}">{column["sensitivity"]}</td>
            </tr>
                    """

        html += """
        </tbody>
    </table>
        """

        # Add recommendations
        html += '<h2 style="color: #2c3e50; margin-top: 30px; margin-bottom: 15px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">Recommendations</h2>'
        for rec in report["recommendations"]:
            priority_class = rec["priority"].lower()
            html += f"""
    <div class="recommendation {priority_class}">
        <h4>{rec["title"]}</h4>
        <p><strong>Priority:</strong> {rec["priority"]}</p>
        <p>{rec["description"]}</p>
    </div>
            """

        # Add category breakdown
        html += '<h2 style="color: #2c3e50; margin-top: 30px; margin-bottom: 15px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">Data Categories</h2>'
        for category, data in report["categories"].items():
            if data["count"] > 0:
                category_title = category.replace("_", " ").title()
                html += f"""
    <div class="category-section">
        <h3>{category_title}</h3>
        <p><strong>Columns Found:</strong> {data["count"]}</p>
        <ul>
                """
                for col in data["columns"][:10]:  # Show first 10
                    html += f"<li>{col['table']}.{col['column']} ({col['sensitivity']})</li>"
                if len(data["columns"]) > 10:
                    html += f"<li>... and {len(data['columns']) - 10} more</li>"
                html += """
        </ul>
    </div>
                """
    else:
        html += """
    <div class="no-data">
        <h2>[OK] No Sensitive Personal Data Detected</h2>
        <p>This database appears to contain no GDPR-sensitive personal information based on column name analysis.</p>
        <p>Note: This scan only analyzes column names. Manual review is still recommended to ensure compliance.</p>
    </div>
        """

    # Add footer without closing body/html tags since this is embedded content
    html += f"""
    <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; text-align: right; color: #666; font-size: 12px;">
        Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} by ThothAI GDPR Scanner
    </div>
    """

    return html
