#!/usr/bin/env python3
"""
Error Classification and Analysis System

Provides taxonomy for error classification, logging, and root cause analysis.
Automatically categorizes failures and helps identify patterns and anomalies.

Error Categories:
- TRANSIENT: Temporary issues (timeout, connection reset, etc.)
- PERMANENT: Persistent errors (invalid request, auth failure, etc.)
- DATA: Data-related issues (malformed response, missing fields, etc.)
- INFRASTRUCTURE: System/infrastructure issues (service down, db unavailable, etc.)
- UNKNOWN: Unclassified errors
"""

import logging
import json
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error classification categories."""
    TRANSIENT = "transient"          # Temporary, retry-able
    PERMANENT = "permanent"          # Won't succeed with retry
    DATA = "data"                    # Malformed/invalid data
    INFRASTRUCTURE = "infrastructure"  # Service/system issues
    TIMEOUT = "timeout"              # Timeout-specific
    AUTH = "authentication"          # Auth failures
    RATE_LIMIT = "rate_limit"       # Rate limiting
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error."""
    error_type: str
    error_message: str
    status_code: Optional[int] = None
    request_data: Optional[Dict] = None
    response_data: Optional[Dict] = None
    stack_trace: Optional[str] = None
    system: str = "unknown"
    question_id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ClassifiedError:
    """Classified error with metadata."""
    context: ErrorContext
    category: ErrorCategory
    severity: ErrorSeverity
    is_flaky: bool = False
    root_cause: Optional[str] = None
    recommended_action: str = "retry"
    confidence: float = 0.8  # Confidence in classification


class ErrorClassifier:
    """Classify and analyze errors."""

    # Error patterns for classification
    TRANSIENT_PATTERNS = [
        r"(?i)(timeout|timed out)",
        r"(?i)(connection reset|connection refused|connection closed)",
        r"(?i)(temporarily unavailable|temporarily|service unavailable)",
        r"(?i)(retry|retrying)",
        r"(?i)(try again|please try again)",
        r"(?i)(503|504)",  # Service Unavailable, Gateway Timeout
    ]

    PERMANENT_PATTERNS = [
        r"(?i)(not found|404)",
        r"(?i)(unauthorized|403|401)",
        r"(?i)(invalid request|bad request|400)",
        r"(?i)(method not allowed|405)",
        r"(?i)(not implemented|501)",
    ]

    DATA_PATTERNS = [
        r"(?i)(json|parse error|malformed)",
        r"(?i)(invalid|unexpected)",
        r"(?i)(missing field|missing key)",
        r"(?i)(type error|value error)",
    ]

    RATE_LIMIT_PATTERNS = [
        r"(?i)(rate limit|rate limited|too many requests)",
        r"(?i)(429)",
    ]

    TIMEOUT_PATTERNS = [
        r"(?i)(timeout|timed out|deadline exceeded)",
    ]

    def __init__(self):
        """Initialize classifier."""
        self.error_cache: Dict[str, ClassifiedError] = {}
        self.error_history: List[ClassifiedError] = []
        self.flaky_tests: Dict[int, int] = defaultdict(int)  # question_id -> failure_count

    def classify(self, error_context: ErrorContext) -> ClassifiedError:
        """Classify an error."""
        # Check cache first
        cache_key = f"{error_context.error_message}_{error_context.status_code}"
        if cache_key in self.error_cache:
            return self.error_cache[cache_key]

        # Determine category
        category = self._determine_category(error_context)
        severity = self._determine_severity(category, error_context)
        root_cause = self._identify_root_cause(error_context, category)
        recommended_action = self._recommend_action(category, error_context)

        classified = ClassifiedError(
            context=error_context,
            category=category,
            severity=severity,
            root_cause=root_cause,
            recommended_action=recommended_action,
            confidence=self._calculate_confidence(category, error_context)
        )

        # Cache and track
        self.error_cache[cache_key] = classified
        self.error_history.append(classified)

        return classified

    def _determine_category(self, context: ErrorContext) -> ErrorCategory:
        """Determine error category from error message and status code."""
        error_str = f"{context.error_type} {context.error_message}".lower()

        # Check specific patterns
        if any(re.search(p, error_str) for p in self.TIMEOUT_PATTERNS):
            return ErrorCategory.TIMEOUT

        if any(re.search(p, error_str) for p in self.RATE_LIMIT_PATTERNS):
            return ErrorCategory.RATE_LIMIT

        if any(re.search(p, error_str) for p in self.TRANSIENT_PATTERNS):
            return ErrorCategory.TRANSIENT

        if any(re.search(p, error_str) for p in self.PERMANENT_PATTERNS):
            return ErrorCategory.PERMANENT

        if any(re.search(p, error_str) for p in self.DATA_PATTERNS):
            return ErrorCategory.DATA

        # Status code analysis
        if context.status_code:
            if context.status_code >= 500:
                return ErrorCategory.INFRASTRUCTURE
            elif context.status_code in [401, 403]:
                return ErrorCategory.AUTH
            elif context.status_code >= 400:
                return ErrorCategory.PERMANENT

        return ErrorCategory.UNKNOWN

    def _determine_severity(self, category: ErrorCategory, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity."""
        # Critical: infrastructure issues, permanent errors
        if category in [ErrorCategory.INFRASTRUCTURE, ErrorCategory.AUTH]:
            return ErrorSeverity.CRITICAL

        # High: permanent, timeout
        if category in [ErrorCategory.PERMANENT, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.HIGH

        # Medium: rate limit, data
        if category in [ErrorCategory.RATE_LIMIT, ErrorCategory.DATA]:
            return ErrorSeverity.MEDIUM

        # Low: transient
        if category == ErrorCategory.TRANSIENT:
            return ErrorSeverity.LOW

        return ErrorSeverity.MEDIUM

    def _identify_root_cause(self, context: ErrorContext, category: ErrorCategory) -> Optional[str]:
        """Identify likely root cause."""
        root_causes = {
            ErrorCategory.TIMEOUT: "Service response time exceeded timeout limit",
            ErrorCategory.RATE_LIMIT: "Too many requests sent, rate limit exceeded",
            ErrorCategory.TRANSIENT: "Temporary service issue, may resolve on retry",
            ErrorCategory.PERMANENT: "Persistent issue with request or service",
            ErrorCategory.DATA: "Invalid or malformed data in request/response",
            ErrorCategory.INFRASTRUCTURE: "Service or infrastructure component down",
            ErrorCategory.AUTH: "Authentication/authorization failure",
            ErrorCategory.UNKNOWN: "Unknown root cause"
        }
        return root_causes.get(category, "Unknown root cause")

    def _recommend_action(self, category: ErrorCategory, context: ErrorContext) -> str:
        """Recommend action for error resolution."""
        actions = {
            ErrorCategory.TIMEOUT: "increase timeout or optimize service performance",
            ErrorCategory.RATE_LIMIT: "implement backoff strategy or increase rate limit",
            ErrorCategory.TRANSIENT: "retry with exponential backoff",
            ErrorCategory.PERMANENT: "fix request or service configuration",
            ErrorCategory.DATA: "validate request/response schema",
            ErrorCategory.INFRASTRUCTURE: "check service health and dependencies",
            ErrorCategory.AUTH: "verify credentials and permissions",
            ErrorCategory.UNKNOWN: "investigate error logs"
        }
        return actions.get(category, "investigate error logs")

    def _calculate_confidence(self, category: ErrorCategory, context: ErrorContext) -> float:
        """Calculate confidence in classification (0-1)."""
        confidence = 0.5

        # Higher confidence if we have status code
        if context.status_code:
            confidence += 0.3

        # Higher confidence if error message is clear
        if context.error_message and len(context.error_message) > 10:
            confidence += 0.2

        # Cap at 1.0
        return min(confidence, 1.0)

    def detect_flaky_test(self, question_id: int, failure_count: int = 1) -> bool:
        """Track potential flaky tests."""
        self.flaky_tests[question_id] += failure_count
        # Mark as flaky if failed more than twice
        return self.flaky_tests[question_id] > 2

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors."""
        if not self.error_history:
            return {'total_errors': 0, 'by_category': {}, 'by_severity': {}}

        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        flaky_count = 0

        for error in self.error_history:
            by_category[error.category.value] += 1
            by_severity[error.severity.value] += 1
            if error.is_flaky:
                flaky_count += 1

        return {
            'total_errors': len(self.error_history),
            'by_category': dict(by_category),
            'by_severity': dict(by_severity),
            'flaky_count': flaky_count,
            'flaky_tests': dict(self.flaky_tests),
            'most_common_category': max(by_category, key=by_category.get) if by_category else None
        }

    def export_errors(self, output_file: str) -> None:
        """Export error log for analysis."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        errors_data = {
            'export_date': datetime.now().isoformat(),
            'total_errors': len(self.error_history),
            'summary': self.get_error_summary(),
            'errors': [
                {
                    'context': asdict(e.context),
                    'category': e.category.value,
                    'severity': e.severity.value,
                    'root_cause': e.root_cause,
                    'recommended_action': e.recommended_action,
                    'confidence': e.confidence
                }
                for e in self.error_history
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(errors_data, f, indent=2)

        logger.info(f"Exported {len(self.error_history)} errors to {output_file}")


def create_error_context(
    error_type: str,
    error_message: str,
    status_code: Optional[int] = None,
    system: str = "unknown",
    question_id: Optional[int] = None,
    **kwargs
) -> ErrorContext:
    """Helper to create error context."""
    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        status_code=status_code,
        system=system,
        question_id=question_id,
        **kwargs
    )
