#!/usr/bin/env python3
"""
Root Cause Analysis System

Analyzes test failures to identify root causes and patterns.
Provides automated failure diagnosis and remediation recommendations.

Features:
- Failure pattern detection
- Correlation analysis
- Anomaly detection
- Remediation suggestions
- Failure trend tracking
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """Analyze test failures for root causes."""

    def __init__(self):
        """Initialize analyzer."""
        self.failure_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.error_correlations: Dict[str, List[str]] = defaultdict(list)
        self.system_state: Dict[str, Any] = {}

    def analyze_failures(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failures in test results."""
        failures = [r for r in results if r.get('error') is not None]

        if not failures:
            return {
                'total_failures': 0,
                'patterns': [],
                'correlations': [],
                'recommendations': []
            }

        # Extract failure patterns
        patterns = self._identify_patterns(failures)
        correlations = self._identify_correlations(failures)
        anomalies = self._detect_anomalies(failures)
        recommendations = self._generate_recommendations(patterns, correlations, anomalies)

        return {
            'total_failures': len(failures),
            'failure_rate': f"{len(failures) / len(results) * 100:.1f}%",
            'patterns': patterns,
            'correlations': correlations,
            'anomalies': anomalies,
            'recommendations': recommendations,
            'analysis_date': datetime.now().isoformat()
        }

    def _identify_patterns(self, failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common failure patterns."""
        error_counts = Counter(f.get('error', 'Unknown') for f in failures)
        sector_failures = defaultdict(int)
        category_failures = defaultdict(int)
        system_failures = defaultdict(int)

        for failure in failures:
            sector_failures[failure.get('sector', 'unknown')] += 1
            category_failures[failure.get('category', 'unknown')] += 1
            system_failures[failure.get('system', 'unknown')] += 1

        patterns = []

        # Most common errors
        for error, count in error_counts.most_common(5):
            patterns.append({
                'type': 'most_common_error',
                'error': error,
                'count': count,
                'percentage': f"{count / len(failures) * 100:.1f}%"
            })

        # Sector-specific patterns
        for sector, count in sorted(sector_failures.items(), key=lambda x: x[1], reverse=True)[:3]:
            patterns.append({
                'type': 'sector_failure_concentration',
                'sector': sector,
                'failure_count': count,
                'insight': f"Sector '{sector}' has highest failure concentration"
            })

        # System-specific patterns
        for system, count in sorted(system_failures.items(), key=lambda x: x[1], reverse=True):
            patterns.append({
                'type': 'system_failure_pattern',
                'system': system,
                'failure_count': count,
                'insight': f"System '{system}' failed {count} times"
            })

        return patterns

    def _identify_correlations(self, failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify correlations between failures."""
        correlations = []

        # Correlate by error type
        error_by_sector = defaultdict(lambda: defaultdict(int))
        for failure in failures:
            error_by_sector[failure.get('error', 'Unknown')][failure.get('sector', 'unknown')] += 1

        for error, sectors in error_by_sector.items():
            if len(sectors) > 1:
                top_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:2]
                correlations.append({
                    'type': 'error_sector_correlation',
                    'error': error,
                    'affected_sectors': top_sectors,
                    'insight': f"Error '{error[:50]}' appears across multiple sectors"
                })

        # Correlate by response time and errors
        high_latency_errors = [f for f in failures if f.get('response_time_ms', 0) > 10000]
        if high_latency_errors:
            correlations.append({
                'type': 'latency_error_correlation',
                'count': len(high_latency_errors),
                'insight': f"{len(high_latency_errors)} failures had very high response times (>10s)"
            })

        return correlations

    def _detect_anomalies(self, failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalous failure patterns."""
        anomalies = []

        # Detect error rate spikes
        error_types = Counter(f.get('error', 'Unknown') for f in failures)
        avg_error_count = len(failures) / max(len(error_types), 1)

        for error, count in error_types.items():
            if count > avg_error_count * 2:
                anomalies.append({
                    'type': 'error_spike',
                    'error': error,
                    'count': count,
                    'severity': 'high',
                    'insight': f"Unusual spike in error: {error}"
                })

        # Detect consecutive failures (possible cascade)
        for i in range(len(failures) - 1):
            if failures[i].get('error') and failures[i+1].get('error'):
                if failures[i].get('system') == failures[i+1].get('system'):
                    anomalies.append({
                        'type': 'cascade_failure',
                        'system': failures[i].get('system'),
                        'consecutive_failures': 2,
                        'insight': f"Consecutive failures in {failures[i].get('system')}"
                    })
                    break  # Only report once

        return anomalies

    def _generate_recommendations(
        self,
        patterns: List[Dict[str, Any]],
        correlations: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate remediation recommendations."""
        recommendations = []

        # Recommendations based on patterns
        for pattern in patterns:
            if 'Timeout' in pattern.get('error', ''):
                recommendations.append({
                    'priority': 'high',
                    'issue': 'Timeout errors detected',
                    'action': 'Increase service timeout or optimize service performance',
                    'details': pattern
                })

            if pattern.get('type') == 'system_failure_pattern':
                recommendations.append({
                    'priority': 'medium',
                    'issue': f"System {pattern.get('system')} experiencing failures",
                    'action': f"Check health status of {pattern.get('system')} service",
                    'details': pattern
                })

        # Recommendations based on correlations
        for correlation in correlations:
            if correlation.get('type') == 'latency_error_correlation':
                recommendations.append({
                    'priority': 'high',
                    'issue': 'High latency errors detected',
                    'action': 'Investigate service performance bottlenecks',
                    'details': correlation
                })

        # Recommendations based on anomalies
        for anomaly in anomalies:
            if anomaly.get('type') == 'cascade_failure':
                recommendations.append({
                    'priority': 'critical',
                    'issue': f"Cascade failure in {anomaly.get('system')}",
                    'action': f"Immediately investigate {anomaly.get('system')} service health",
                    'details': anomaly
                })

        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda r: priority_order.get(r.get('priority', 'low'), 4))

        return recommendations

    def track_failure_trends(
        self,
        current_results: List[Dict[str, Any]],
        historical_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Track failure trends over time."""
        current_failures = len([r for r in current_results if r.get('error')])
        current_rate = current_failures / len(current_results) * 100 if current_results else 0

        trend = {
            'current_failure_rate': f"{current_rate:.1f}%",
            'current_failure_count': current_failures,
            'trend': 'stable',
            'change_percent': 0.0
        }

        if historical_results:
            historical_failures = len([r for r in historical_results if r.get('error')])
            historical_rate = historical_failures / len(historical_results) * 100 if historical_results else 0

            change = current_rate - historical_rate
            trend['previous_failure_rate'] = f"{historical_rate:.1f}%"
            trend['change_percent'] = f"{change:+.1f}%"

            if change > 5:
                trend['trend'] = 'degrading'
            elif change < -5:
                trend['trend'] = 'improving'

        return trend

    def generate_failure_report(
        self,
        results: List[Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> str:
        """Generate detailed failure report."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_results/failure_analysis_{timestamp}.json"

        analysis = self.analyze_failures(results)

        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'failures': [r for r in results if r.get('error')]
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated failure report: {output_file}")
        return output_file
