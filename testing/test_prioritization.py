#!/usr/bin/env python3
"""
Test Prioritization System

Prioritizes tests for faster feedback:
- Risk-based ordering
- Regression probability scoring
- Critical path analysis
- Fail-fast strategies

Features:
- Impact-based prioritization
- Failure history tracking
- Coverage analysis
- Dynamic priority adjustment
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TestPriority:
    """Test priority information."""
    test_id: int
    test_name: str
    priority_score: float  # 0-100
    risk_level: str  # critical, high, medium, low
    failure_history_count: int
    last_failure_date: Optional[str]
    coverage_impact: float  # 0-1
    execution_time_ms: float
    reason: str


class TestPrioritizer:
    """Prioritize tests for execution."""

    def __init__(self):
        """Initialize prioritizer."""
        self.test_history: Dict[int, Dict[str, Any]] = {}
        self.failure_counts: Dict[int, int] = defaultdict(int)
        self.execution_times: Dict[int, float] = {}

    def prioritize_tests(
        self,
        tests: List[Dict[str, Any]],
        historical_results: Optional[List[Dict[str, Any]]] = None,
        risk_weights: Optional[Dict[str, float]] = None
    ) -> List[TestPriority]:
        """
        Prioritize tests for execution.

        Risk weights can include:
        - failure_rate: recent failure rate (0-1)
        - criticality: business impact (0-1)
        - coverage: code coverage impact (0-1)
        - execution_time: inverse of speed (0-1)
        """
        if risk_weights is None:
            risk_weights = {
                'failure_rate': 0.4,
                'criticality': 0.3,
                'coverage': 0.2,
                'execution_time': 0.1
            }

        # Build test history from historical results
        if historical_results:
            self._build_history(historical_results)

        priorities = []

        for test in tests:
            test_id = test.get('id')
            test_name = test.get('question', 'unknown')

            # Calculate components
            failure_rate = self._calculate_failure_rate(test_id)
            criticality = self._calculate_criticality(test)
            coverage_impact = self._calculate_coverage_impact(test)
            execution_time = self._normalize_execution_time(
                self.execution_times.get(test_id, 100)
            )

            # Calculate weighted score
            priority_score = (
                failure_rate * risk_weights['failure_rate'] * 100 +
                criticality * risk_weights['criticality'] * 100 +
                coverage_impact * risk_weights['coverage'] * 100 +
                execution_time * risk_weights['execution_time'] * 100
            )

            # Determine risk level
            if priority_score >= 80:
                risk_level = 'critical'
            elif priority_score >= 60:
                risk_level = 'high'
            elif priority_score >= 40:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            reason = self._explain_priority(test_id, failure_rate, criticality)

            priority = TestPriority(
                test_id=test_id,
                test_name=test_name,
                priority_score=round(priority_score, 1),
                risk_level=risk_level,
                failure_history_count=self.failure_counts.get(test_id, 0),
                last_failure_date=self.test_history.get(test_id, {}).get('last_failure'),
                coverage_impact=round(coverage_impact, 2),
                execution_time_ms=self.execution_times.get(test_id, 0),
                reason=reason
            )
            priorities.append(priority)

        # Sort by priority score (highest first)
        priorities.sort(key=lambda p: p.priority_score, reverse=True)

        return priorities

    def _build_history(self, historical_results: List[Dict[str, Any]]) -> None:
        """Build test history from historical results."""
        for result in historical_results:
            test_id = result.get('question_id')
            if test_id not in self.test_history:
                self.test_history[test_id] = {
                    'total_runs': 0,
                    'failures': 0,
                    'last_failure': None
                }

            self.test_history[test_id]['total_runs'] += 1
            if result.get('error'):
                self.failure_counts[test_id] += 1
                self.test_history[test_id]['failures'] += 1
                self.test_history[test_id]['last_failure'] = result.get('timestamp')

            # Track execution time
            if test_id not in self.execution_times:
                self.execution_times[test_id] = result.get('response_time_ms', 100)
            else:
                # Moving average
                self.execution_times[test_id] = (
                    self.execution_times[test_id] * 0.7 +
                    result.get('response_time_ms', 100) * 0.3
                )

    def _calculate_failure_rate(self, test_id: int) -> float:
        """Calculate failure rate for a test (0-1)."""
        if test_id not in self.test_history:
            return 0.0

        history = self.test_history[test_id]
        if history['total_runs'] == 0:
            return 0.0

        return history['failures'] / history['total_runs']

    def _calculate_criticality(self, test: Dict[str, Any]) -> float:
        """Calculate business criticality (0-1)."""
        difficulty = test.get('difficulty', 'medium')
        category = test.get('category', 'simple')

        # Critical tests are higher difficulty or complex
        criticality = 0.5  # baseline

        if difficulty == 'hard':
            criticality += 0.25
        elif difficulty == 'medium':
            criticality += 0.15

        if category in ['comparative', 'complex']:
            criticality += 0.25

        return min(criticality, 1.0)

    def _calculate_coverage_impact(self, test: Dict[str, Any]) -> float:
        """Calculate coverage impact (0-1)."""
        sector = test.get('sector')
        level = test.get('level')

        # Different sectors/levels have different coverage impact
        sector_weight = {
            'transport': 0.15,
            'power': 0.15,
            'industrial': 0.12,
            'agriculture': 0.12,
            'buildings': 0.12,
            'waste': 0.10,
        }

        level_weight = {
            'country': 0.35,
            'state': 0.30,
            'city': 0.25,
        }

        impact = (
            sector_weight.get(sector, 0.1) +
            level_weight.get(level, 0.25)
        )

        return min(impact, 1.0)

    def _normalize_execution_time(self, execution_time_ms: float) -> float:
        """Normalize execution time (0-1, lower = faster = higher priority)."""
        # Faster tests should have higher priority for fail-fast
        # Assume 100ms is baseline
        normalized = min(execution_time_ms / 1000, 1.0)
        return 1.0 - normalized  # Invert so faster = higher

    def _explain_priority(self, test_id: int, failure_rate: float, criticality: float) -> str:
        """Generate explanation for priority."""
        reasons = []

        if failure_rate > 0.2:
            reasons.append(f"{failure_rate*100:.0f}% failure rate")

        if criticality > 0.7:
            reasons.append("High business criticality")

        if self.failure_counts.get(test_id, 0) > 5:
            reasons.append("Multiple recent failures")

        return " | ".join(reasons) if reasons else "Standard priority"

    def get_smoke_test_suite(
        self,
        priorities: List[TestPriority],
        count: int = 10
    ) -> List[TestPriority]:
        """Get smoke test suite (critical tests only)."""
        return [p for p in priorities if p.risk_level in ['critical', 'high']][:count]

    def get_sanity_test_suite(
        self,
        priorities: List[TestPriority],
        count: int = 20
    ) -> List[TestPriority]:
        """Get sanity test suite (mix of priorities)."""
        critical = [p for p in priorities if p.risk_level == 'critical']
        high = [p for p in priorities if p.risk_level == 'high']
        medium = [p for p in priorities if p.risk_level == 'medium']

        # Mix of different risk levels
        sanity = critical + high[:count//2] + medium[:count//4]
        return sanity[:count]

    def generate_priority_report(
        self,
        priorities: List[TestPriority],
        output_file: str = "test_results/test_priority_report.json"
    ) -> str:
        """Generate test priority report."""
        import json
        from pathlib import Path

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(priorities),
            'by_risk_level': self._group_by_risk(priorities),
            'top_10_highest_priority': [
                {
                    'test_id': p.test_id,
                    'test_name': p.test_name,
                    'priority_score': p.priority_score,
                    'risk_level': p.risk_level,
                    'reason': p.reason
                }
                for p in priorities[:10]
            ],
            'all_priorities': [
                {
                    'test_id': p.test_id,
                    'priority_score': p.priority_score,
                    'risk_level': p.risk_level,
                    'failure_history': p.failure_history_count,
                    'coverage_impact': p.coverage_impact
                }
                for p in priorities
            ]
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated priority report: {output_file}")
        return output_file

    def _group_by_risk(self, priorities: List[TestPriority]) -> Dict[str, int]:
        """Group tests by risk level."""
        groups = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for p in priorities:
            groups[p.risk_level] += 1
        return groups
