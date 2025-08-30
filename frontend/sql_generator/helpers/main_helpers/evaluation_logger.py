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

# Unless required by applicable law or agreed to in writing, software
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
Advanced logging system for the enhanced evaluation flow.

Provides comprehensive tracking of all evaluation decisions, auxiliary agent
usage, performance metrics, and escalation events for analysis and debugging.
"""

import logging
import json
import time
from typing import Dict, Any
from datetime import datetime
from enum import Enum

from agents.core.agent_result_models import EnhancedEvaluationResult, EvaluationStatus

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for evaluation events"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EvaluationEventType(Enum):
    """Types of evaluation events to log"""
    EVALUATION_START = "evaluation_start"
    EVALUATION_COMPLETE = "evaluation_complete"
    CASE_CLASSIFICATION = "case_classification"
    AUXILIARY_AGENT_RUN = "auxiliary_agent_run"
    ESCALATION_TRIGGERED = "escalation_triggered"
    SQL_SELECTION = "sql_selection"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_OCCURRED = "error_occurred"


class EvaluationLogger:
    """Advanced logging system for evaluation flow tracking"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"eval_{int(time.time())}"
        self.events = []
        self.start_time = None
        self.metrics = {}
        
    def log_event(
        self,
        event_type: EvaluationEventType,
        level: LogLevel = LogLevel.INFO,
        message: str = "",
        data: Dict[str, Any] = None,
        sql_index: int = None,
        agent_name: str = None
    ) -> None:
        """
        Log an evaluation event with structured data.
        
        Args:
            event_type: Type of event being logged
            level: Log level for the event
            message: Human-readable message
            data: Additional structured data
            sql_index: Index of SQL being processed (if applicable)
            agent_name: Name of agent involved (if applicable)
        """
        timestamp = datetime.utcnow().isoformat()
        
        event = {
            "session_id": self.session_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "level": level.value,
            "message": message,
            "sql_index": sql_index,
            "agent_name": agent_name,
            "data": data or {}
        }
        
        self.events.append(event)
        
        # Also log to standard logger
        log_func = {
            LogLevel.DEBUG: logger.debug,
            LogLevel.INFO: logger.info,
            LogLevel.WARNING: logger.warning,
            LogLevel.ERROR: logger.error,
            LogLevel.CRITICAL: logger.critical
        }[level]
        
        log_message = f"[{self.session_id}] {event_type.value}: {message}"
        if data:
            log_message += f" | Data: {json.dumps(data, default=str)}"
            
        log_func(log_message)
    
    def start_evaluation(
        self,
        question: str,
        sql_count: int,
        functionality_level: str,
        test_count: int = 0
    ) -> None:
        """Log evaluation start with context information."""
        self.start_time = time.time()
        
        self.log_event(
            EvaluationEventType.EVALUATION_START,
            LogLevel.INFO,
            f"Starting enhanced evaluation for {sql_count} SQLs",
            {
                "question": question,
                "sql_count": sql_count,
                "functionality_level": functionality_level,
                "test_count": test_count,
                "timestamp": self.start_time
            }
        )
    
    def log_case_classification(
        self,
        case: str,
        pass_rates: Dict[str, float],
        perfect_count: int,
        borderline_count: int,
        failed_count: int
    ) -> None:
        """Log case classification results."""
        self.log_event(
            EvaluationEventType.CASE_CLASSIFICATION,
            LogLevel.INFO,
            f"Classified as Case {case}",
            {
                "case": case,
                "pass_rates": pass_rates,
                "perfect_count": perfect_count,
                "borderline_count": borderline_count,
                "failed_count": failed_count,
                "best_pass_rate": max(pass_rates.values()) if pass_rates else 0.0,
                "worst_pass_rate": min(pass_rates.values()) if pass_rates else 0.0,
                "avg_pass_rate": sum(pass_rates.values()) / len(pass_rates) if pass_rates else 0.0
            }
        )
    
    def log_auxiliary_agent_execution(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        result: Any,
        execution_time_ms: float,
        success: bool = True
    ) -> None:
        """Log auxiliary agent execution details."""
        self.log_event(
            EvaluationEventType.AUXILIARY_AGENT_RUN,
            LogLevel.INFO if success else LogLevel.ERROR,
            f"{'Successfully executed' if success else 'Failed to execute'} {agent_name}",
            {
                "agent_name": agent_name,
                "input_summary": {
                    "question_length": len(input_data.get("question", "")),
                    "schema_tables": input_data.get("schema_tables", 0),
                    "sql_count": len(input_data.get("sqls", [])),
                    "test_count": len(input_data.get("tests", []))
                },
                "result_summary": {
                    "has_result": result is not None,
                    "result_type": type(result).__name__ if result else None
                },
                "execution_time_ms": execution_time_ms,
                "success": success
            },
            agent_name=agent_name
        )
    
    def log_sql_selection(
        self,
        case: str,
        selected_index: int,
        selected_sql: str,
        reasoning: str,
        confidence: float = None
    ) -> None:
        """Log SQL selection decision."""
        self.log_event(
            EvaluationEventType.SQL_SELECTION,
            LogLevel.INFO,
            f"Case {case}: Selected SQL #{selected_index + 1}",
            {
                "case": case,
                "selected_index": selected_index,
                "selected_sql_preview": selected_sql[:200] + "..." if len(selected_sql) > 200 else selected_sql,
                "reasoning_preview": reasoning[:300] + "..." if len(reasoning) > 300 else reasoning,
                "confidence": confidence,
                "sql_length": len(selected_sql)
            },
            sql_index=selected_index
        )
    
    def log_escalation(
        self,
        reason: str,
        current_level: str,
        next_level: str,
        failure_context: str,
        failed_sql_count: int
    ) -> None:
        """Log escalation event."""
        self.log_event(
            EvaluationEventType.ESCALATION_TRIGGERED,
            LogLevel.WARNING,
            f"Escalating from {current_level} to {next_level}",
            {
                "reason": reason,
                "current_level": current_level,
                "next_level": next_level,
                "failure_context": failure_context,
                "failed_sql_count": failed_sql_count
            }
        )
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        category: str = "general"
    ) -> None:
        """Log performance metric."""
        self.metrics[metric_name] = {
            "value": value,
            "unit": unit,
            "category": category,
            "timestamp": time.time()
        }
        
        self.log_event(
            EvaluationEventType.PERFORMANCE_METRIC,
            LogLevel.DEBUG,
            f"Metric {metric_name}: {value}{unit}",
            {
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "category": category
            }
        )
    
    def log_error(
        self,
        error_message: str,
        error_type: str,
        context: Dict[str, Any] = None,
        sql_index: int = None,
        agent_name: str = None
    ) -> None:
        """Log error event."""
        self.log_event(
            EvaluationEventType.ERROR_OCCURRED,
            LogLevel.ERROR,
            error_message,
            {
                "error_type": error_type,
                "context": context or {},
                "timestamp": time.time()
            },
            sql_index=sql_index,
            agent_name=agent_name
        )
    
    def complete_evaluation(
        self,
        result: EnhancedEvaluationResult,
        final_status: EvaluationStatus
    ) -> None:
        """Log evaluation completion with final results."""
        end_time = time.time()
        total_time = (end_time - self.start_time) * 1000 if self.start_time else 0
        
        self.log_event(
            EvaluationEventType.EVALUATION_COMPLETE,
            LogLevel.INFO,
            f"Evaluation completed with status {final_status.value}",
            {
                "final_status": final_status.value,
                "evaluation_case": result.evaluation_case,
                "selected_sql_index": result.selected_sql_index,
                "auxiliary_agents_used": result.auxiliary_agents_used,
                "processing_time_ms": total_time,
                "requires_escalation": result.requires_escalation,
                "best_pass_rate": result.best_pass_rate,
                "total_events": len(self.events),
                "session_metrics": self.metrics
            }
        )
        
        # Log final performance summary
        self.log_performance_metric("total_evaluation_time", total_time, "ms", "performance")
        self.log_performance_metric("auxiliary_agents_count", len(result.auxiliary_agents_used), "", "usage")
    
    def get_evaluation_summary(self) -> Dict[str, Any]:
        """Get comprehensive evaluation summary."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "total_events": len(self.events),
            "event_types": {
                event_type.value: len([e for e in self.events if e["event_type"] == event_type.value])
                for event_type in EvaluationEventType
            },
            "log_levels": {
                level.value: len([e for e in self.events if e["level"] == level.value])
                for level in LogLevel
            },
            "metrics": self.metrics,
            "events": self.events
        }
    
    def export_logs(self, format: str = "json") -> str:
        """Export evaluation logs in specified format."""
        summary = self.get_evaluation_summary()
        
        if format == "json":
            return json.dumps(summary, indent=2, default=str)
        elif format == "csv":
            # Basic CSV export of events
            lines = ["timestamp,event_type,level,message,agent_name,sql_index"]
            for event in self.events:
                lines.append(f"{event['timestamp']},{event['event_type']},{event['level']},\"{event['message']}\",{event['agent_name'] or ''},{event['sql_index'] or ''}")
            return "\n".join(lines)
        else:
            return str(summary)


def create_evaluation_logger(session_id: str = None) -> EvaluationLogger:
    """
    Create a new evaluation logger instance.
    
    Args:
        session_id: Optional session identifier
        
    Returns:
        Configured EvaluationLogger instance
    """
    return EvaluationLogger(session_id)