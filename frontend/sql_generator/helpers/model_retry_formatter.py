"""Utilities to build structured ModelRetry messages for SQL agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from helpers.logging_config import get_logger

logger = get_logger(__name__)


class ErrorCategory(str, Enum):
    """High level categories for ModelRetry messages."""

    SYNTAX_ERROR = "SYNTAX_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    EMPTY_RESULT = "EMPTY_RESULT"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"


@dataclass
class ErrorContext:
    """Context payload used to build ModelRetry messages."""

    sql: str = ""
    db_type: str = ""
    question: str = ""
    retry_count: int = 0
    error_message: str = ""
    exception: Optional[Exception] = None
    validation_results: Optional[List[Dict[str, Any]]] = None
    failed_tests: Optional[List[str]] = None
    evidence_summary: Optional[Dict[str, Any]] = None
    explain_error: str = ""
    available_tables: Optional[List[str]] = None
    additional_hints: Optional[List[str]] = None
    previous_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render_error_detail(self) -> str:
        """Return the best available error description."""

        if self.error_message:
            return self.error_message
        if self.exception is not None:
            return f"{type(self.exception).__name__}: {self.exception}"
        if self.explain_error:
            return self.explain_error
        return "Validation failed without extra detail"

    @property
    def attempt_number(self) -> int:
        """Return a 1-indexed attempt counter for human friendly messages."""

        return (self.retry_count or 0) + 1

    @property
    def formatted_db_label(self) -> str:
        return (self.db_type or "unknown").upper()


class ModelRetryFormatter:
    """Factory for ModelRetry messages consumed by PydanticAI agents."""

    TOP_SECTION = "MODEL_RETRY::{category}\nAttempt: {attempt}\nDatabase: {database}\n"

    @classmethod
    def format_error(cls, category: ErrorCategory, context: ErrorContext) -> str:
        """Return a structured message to feed back into the agent."""

        body_sections: List[str] = []

        top = cls.TOP_SECTION.format(
            category=category.value,
            attempt=context.attempt_number,
            database=context.formatted_db_label,
        )
        body_sections.append(top)

        if context.question:
            body_sections.append(cls._format_block("User Question", context.question))

        if context.sql:
            body_sections.append(cls._format_sql(context.sql))

        body_sections.append(
            cls._format_block("Primary Issue", context.render_error_detail())
        )

        category_section = cls._render_category_section(category, context)
        if category_section:
            body_sections.append(category_section)

        if context.previous_errors:
            previous = "\n".join(f"- {item}" for item in context.previous_errors[-5:])
            body_sections.append(cls._format_block("Previous Attempts", previous))

        guidance = cls._build_guidance(category, context)
        if guidance:
            body_sections.append(cls._format_list_block("Action Items", guidance))

        return "\n\n".join(section for section in body_sections if section).strip()

    @classmethod
    def build_history_entry(cls, category: ErrorCategory, context: ErrorContext) -> str:
        """Generate a concise entry describing this retry for future runs."""

        detail = context.render_error_detail()
        detail = detail.replace("\n", " ").strip()
        if len(detail) > 160:
            detail = f"{detail[:157]}..."
        return f"Attempt {context.attempt_number} · {category.value}: {detail}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _format_block(title: str, content: str) -> str:
        clean = content.strip()
        if not clean:
            return ""
        return f"{title}:\n  {clean.replace('\n', '\n  ')}"

    @staticmethod
    def _format_list_block(title: str, items: Iterable[str]) -> str:
        rows = [item.strip() for item in items if item]
        if not rows:
            return ""
        bullet_lines = "\n".join(f"  - {line}" for line in rows)
        return f"{title}:\n{bullet_lines}"

    @staticmethod
    def _format_sql(sql: str) -> str:
        if not sql.strip():
            return ""
        return f"Candidate SQL:\n```sql\n{sql.strip()}\n```"

    @classmethod
    def _render_category_section(cls, category: ErrorCategory, context: ErrorContext) -> str:
        if category == ErrorCategory.VALIDATION_FAILED:
            return cls._render_validation_section(context)
        if category == ErrorCategory.EXECUTION_ERROR:
            return cls._render_execution_section(context)
        if category == ErrorCategory.EMPTY_RESULT:
            return cls._render_empty_result_section(context)
        if category == ErrorCategory.SYNTAX_ERROR:
            return cls._render_syntax_section(context)
        if category == ErrorCategory.EVIDENCE_MISMATCH:
            return cls._render_evidence_section(context)
        if category == ErrorCategory.SCHEMA_ERROR:
            return cls._render_schema_section(context)
        return ""

    @classmethod
    def _render_validation_section(cls, context: ErrorContext) -> str:
        if not context.validation_results:
            return ""
        failed = [item for item in context.validation_results if not item.get("passed", False)]
        passed = [item for item in context.validation_results if item.get("passed", False)]
        lines: List[str] = []
        if failed:
            lines.append("Failed Checks:")
            for idx, item in enumerate(failed, 1):
                name = item.get("name") or item.get("id") or f"Test {idx}"
                detail = item.get("error") or item.get("detail") or "Validation failed"
                lines.append(f"  • {name}: {detail}")
        if passed:
            lines.append("Passed Checks:")
            lines.append(f"  • {len(passed)} validations succeeded")
        return "\n".join(lines)

    @classmethod
    def _render_execution_section(cls, context: ErrorContext) -> str:
        hint_lines: List[str] = []
        detail = context.render_error_detail().lower()
        if "does not exist" in detail and "column" in detail:
            hint_lines.extend(
                [
                    "Verify column names and aliases",
                    "Ensure all referenced tables expose the column",
                    "Check case sensitivity requirements",
                ]
            )
        elif "does not exist" in detail and "table" in detail:
            hint_lines.extend(
                [
                    "Confirm table name and schema prefix",
                    "Ensure table is available in workspace",
                    "Check spelling of identifiers",
                ]
            )
        elif "syntax" in detail or "parse" in detail:
            hint_lines.extend(
                [
                    "Review clause ordering (SELECT → FROM → WHERE → GROUP BY → ORDER BY)",
                    "Check for missing commas or parentheses",
                    "Ensure quotes match and strings are terminated",
                ]
            )
        elif "group by" in detail:
            hint_lines.extend(
                [
                    "Every SELECT column must be aggregated or appear in GROUP BY",
                    "Avoid using aliases not defined before GROUP BY",
                    "Validate aggregate expressions",
                ]
            )
        elif "join" in detail:
            hint_lines.extend(
                [
                    "Verify join predicates reference existing columns",
                    "Check join type and ensure ON clause is present",
                    "Confirm aliases are defined",
                ]
            )
        else:
            hint_lines.extend(
                [
                    "Run simplified version of the query to isolate the issue",
                    "Check data types used in comparisons and functions",
                    "Ensure database-specific functions are correct",
                ]
            )
        if hint_lines:
            return cls._format_list_block("Debugging Tips", hint_lines)
        return ""

    @classmethod
    def _render_empty_result_section(cls, context: ErrorContext) -> str:
        hints = [
            "Relax restrictive WHERE filters",
            "Verify JOIN predicates do not exclude all rows",
            "Check date ranges against available data",
            "Inspect underlying tables with COUNT(*)",
        ]
        if context.available_tables:
            hints.append(
                f"Tables available: {', '.join(context.available_tables[:6])}{' …' if len(context.available_tables) > 6 else ''}"
            )
        return cls._format_list_block("Investigation Steps", hints)

    @classmethod
    def _render_syntax_section(cls, context: ErrorContext) -> str:
        hints = [
            "Confirm clause order (SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY)",
            "Ensure identifiers are quoted for the target database",
            "Replace LIMIT/OFFSET with database-specific equivalents if needed",
        ]
        if context.db_type.lower() in {"sqlserver", "mssql"}:
            hints.append("Use TOP n or OFFSET … FETCH syntax instead of LIMIT")
        if context.db_type.lower() == "oracle":
            hints.append("Consider FETCH FIRST n ROWS ONLY or ROWNUM filters")
        return cls._format_list_block("Syntax Guidance", hints)

    @classmethod
    def _render_evidence_section(cls, context: ErrorContext) -> str:
        lines: List[str] = []
        if context.failed_tests:
            lines.append("Evidence Constraints Violated:")
            for entry in context.failed_tests:
                lines.append(f"  • {entry}")
        if context.evidence_summary:
            strict = context.evidence_summary.get("strict")
            weak = context.evidence_summary.get("weak")
            irrelevant = context.evidence_summary.get("irrelevant")
            summary = [
                f"STRICT={strict}" if strict is not None else "",
                f"WEAK={weak}" if weak is not None else "",
                f"IRRELEVANT={irrelevant}" if irrelevant is not None else "",
            ]
            formatted = ", ".join(filter(None, summary))
            if formatted:
                lines.append(f"Classification: {formatted}")
        return "\n".join(lines)

    @staticmethod
    def _build_guidance(category: ErrorCategory, context: ErrorContext) -> List[str]:
        custom = list(context.additional_hints or [])
        if category == ErrorCategory.VALIDATION_FAILED:
            base = [
                "Address each failed validation before resubmitting",
                "Keep passing checks intact while fixing issues",
                "Double-check join logic and filters mentioned above",
            ]
            return custom or base
        if category == ErrorCategory.EXECUTION_ERROR:
            base = [
                "Run simplified snippets locally to narrow the failure",
                "Validate object names against the schema supplied",
                "Ensure functions and operators match the database dialect",
            ]
            return custom or base
        if category == ErrorCategory.EMPTY_RESULT:
            base = [
                "Ensure the question truly expects existing data",
                "Relax filters and rebuild to reach non-empty result",
                "Confirm referenced tables contain data in the time range",
            ]
            return custom or base
        if category == ErrorCategory.SYNTAX_ERROR:
            base = [
                "Fix the syntax issue identified above",
                "Re-run EXPLAIN to validate the updated query",
                "Keep result columns aligned with the question",
            ]
            return custom or base
        if category == ErrorCategory.EVIDENCE_MISMATCH:
            base = [
                "Apply each STRICT requirement exactly as described",
                "Capture key filters or aggregations from evidence",
                "Re-evaluate unit tests mentally before resubmitting",
            ]
            return custom or base
        return custom

