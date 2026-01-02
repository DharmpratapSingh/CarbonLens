#!/usr/bin/env python3
"""
Baseline Management for Performance Regression Detection

Manages performance baselines for comparative testing. Stores baseline response times
and detects regressions when performance degrades.

Features:
- Store baseline response times per question and system
- Detect performance regressions with configurable thresholds
- Track P95/P99 latencies
- Generate regression reports
- Trend analysis over time
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from statistics import mean, median, stdev
import sys

logger = logging.getLogger(__name__)


class PerformanceBaseline:
    """Store and manage performance baselines."""

    def __init__(self, baseline_dir: str = "test_results/baselines"):
        """Initialize baseline manager."""
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.baselines: Dict[str, Dict[str, float]] = {}
        self.load_latest_baseline()

    def load_latest_baseline(self) -> bool:
        """Load the latest baseline file."""
        baseline_files = sorted(self.baseline_dir.glob("baseline_*.json"))
        if not baseline_files:
            logger.debug("No baseline files found, starting fresh")
            return False

        latest = baseline_files[-1]
        try:
            with open(latest, 'r') as f:
                data = json.load(f)
                self.baselines = data.get('baselines', {})
                logger.info(f"Loaded baseline from: {latest.name}")
                return True
        except Exception as e:
            logger.error(f"Error loading baseline: {e}")
            return False

    def save_baseline(self, test_results: List[Dict[str, Any]]) -> str:
        """Save current test results as baseline."""
        baselines = {}
        for result in test_results:
            if result['error'] is None:  # Only include successful tests
                key = f"{result['system']}_{result['question_id']}"
                baselines[key] = {
                    'response_time_ms': result['response_time_ms'],
                    'question_id': result['question_id'],
                    'system': result['system'],
                    'timestamp': result['timestamp']
                }

        baseline_data = {
            'timestamp': datetime.now().isoformat(),
            'total_baselines': len(baselines),
            'baselines': baselines
        }

        filename = self.baseline_dir / f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(baseline_data, f, indent=2)

        self.baselines = baselines
        logger.info(f"Saved baseline to: {filename.name} with {len(baselines)} entries")
        return str(filename)

    def compare_results(
        self,
        current_results: List[Dict[str, Any]],
        threshold_percent: float = 10.0,
        percentile: str = 'median'
    ) -> Dict[str, Any]:
        """
        Compare current results against baseline.

        Args:
            current_results: List of test results to compare
            threshold_percent: Percentage threshold for regression alert (default 10%)
            percentile: 'median', 'p95', or 'p99' for comparison

        Returns:
            Dictionary with regression analysis
        """
        if not self.baselines:
            logger.warning("No baseline data available for comparison")
            return {'has_baselines': False, 'regressions': []}

        regressions = []
        improvements = []
        stable = []

        for result in current_results:
            if result['error'] is not None:
                continue

            key = f"{result['system']}_{result['question_id']}"
            if key not in self.baselines:
                continue

            baseline_time = self.baselines[key]['response_time_ms']
            current_time = result['response_time_ms']
            delta_ms = current_time - baseline_time
            delta_percent = (delta_ms / baseline_time) * 100 if baseline_time > 0 else 0

            comparison = {
                'question_id': result['question_id'],
                'system': result['system'],
                'baseline_ms': baseline_time,
                'current_ms': current_time,
                'delta_ms': round(delta_ms, 2),
                'delta_percent': round(delta_percent, 2),
                'category': result.get('category', 'unknown'),
                'sector': result.get('sector', 'unknown'),
            }

            if delta_percent > threshold_percent:
                regressions.append(comparison)
            elif delta_percent < -threshold_percent:
                improvements.append(comparison)
            else:
                stable.append(comparison)

        return {
            'has_baselines': True,
            'comparison_date': datetime.now().isoformat(),
            'threshold_percent': threshold_percent,
            'regressions': regressions,
            'improvements': improvements,
            'stable': stable,
            'total_compared': len(regressions) + len(improvements) + len(stable),
            'regression_count': len(regressions),
            'improvement_count': len(improvements),
            'stable_count': len(stable),
            'regression_percent': round(
                (len(regressions) / (len(regressions) + len(improvements) + len(stable)) * 100)
                if (len(regressions) + len(improvements) + len(stable)) > 0
                else 0, 2
            )
        }

    def get_percentile_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculate P95, P99 latencies per system."""
        stats = {}

        systems = set(r['system'] for r in results if r['error'] is None)
        for system in systems:
            times = [r['response_time_ms'] for r in results if r['system'] == system and r['error'] is None]
            if times:
                times_sorted = sorted(times)
                n = len(times_sorted)
                stats[system] = {
                    'mean': round(mean(times), 2),
                    'median': round(median(times), 2),
                    'min': round(min(times), 2),
                    'max': round(max(times), 2),
                    'stdev': round(stdev(times), 2) if len(times) > 1 else 0,
                    'p95': round(times_sorted[int(n * 0.95)], 2),
                    'p99': round(times_sorted[int(n * 0.99)], 2),
                    'count': n
                }

        return stats

    def detect_performance_anomalies(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect performance anomalies using statistical analysis."""
        stats = self.get_percentile_stats(results)
        anomalies = {'anomalous_tests': []}

        for result in results:
            if result['error'] is not None:
                continue

            system = result['system']
            if system not in stats:
                continue

            time_ms = result['response_time_ms']
            sys_stats = stats[system]

            # Check if response time is beyond mean + 2*stdev (anomaly threshold)
            if sys_stats['stdev'] > 0:
                z_score = (time_ms - sys_stats['mean']) / sys_stats['stdev']
                if z_score > 2.5:  # Beyond 2.5 standard deviations
                    anomalies['anomalous_tests'].append({
                        'question_id': result['question_id'],
                        'system': system,
                        'response_time_ms': time_ms,
                        'mean_ms': sys_stats['mean'],
                        'stdev_ms': sys_stats['stdev'],
                        'z_score': round(z_score, 2),
                        'category': result.get('category'),
                        'severity': 'high' if z_score > 3.0 else 'medium'
                    })

        return {
            'statistics': stats,
            'anomalies': anomalies
        }
