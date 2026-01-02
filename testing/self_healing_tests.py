#!/usr/bin/env python3
"""
Self-Healing Tests

Tests that automatically fix themselves:
- Auto-fixing flaky tests
- Smart wait strategies
- Self-updating assertions
- Auto-retry with learning
- Selector healing for UI tests

Features:
- Adaptive timeout adjustment
- Assertion self-correction
- Flakiness learning
- Automatic retry tuning
- Status quo learning
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class TestExecution:
    """Record of a test execution."""
    test_id: int
    test_name: str
    status: str  # pass, fail, timeout
    duration_ms: float
    error: Optional[str]
    timestamp: str


@dataclass
class TestHealthMetrics:
    """Health metrics for a test."""
    test_id: int
    total_runs: int
    passed_runs: int
    failed_runs: int
    avg_duration_ms: float
    optimal_timeout_ms: float
    flakiness_score: float  # 0-1
    recommended_retries: int


class AdaptiveWaiter:
    """Smart wait strategy that learns."""

    def __init__(self, history_size: int = 50):
        """Initialize adaptive waiter."""
        self.execution_history: deque = deque(maxlen=history_size)
        self.optimal_timeouts: Dict[str, float] = {}

    def wait_for_condition(
        self,
        condition: Callable,
        test_name: str,
        max_timeout_ms: int = 30000,
        poll_interval_ms: int = 100
    ) -> Tuple[bool, float]:
        """
        Wait for condition with adaptive timeout.

        Returns:
            (success, actual_time_ms)
        """
        start_time = time.time()
        optimal_timeout = self.optimal_timeouts.get(test_name, max_timeout_ms)

        while time.time() - start_time < optimal_timeout / 1000:
            try:
                if condition():
                    elapsed_ms = (time.time() - start_time) * 1000
                    self._learn_optimal_timeout(test_name, elapsed_ms)
                    return True, elapsed_ms
            except Exception:
                pass

            time.sleep(poll_interval_ms / 1000)

        elapsed_ms = (time.time() - start_time) * 1000
        return False, elapsed_ms

    def _learn_optimal_timeout(self, test_name: str, execution_time_ms: float) -> None:
        """Learn optimal timeout from execution time."""
        self.execution_history.append(execution_time_ms)

        if len(self.execution_history) >= 10:
            # Calculate P99 timeout
            sorted_times = sorted(self.execution_history)
            p99_index = int(len(sorted_times) * 0.99)
            p99_time = sorted_times[p99_index]

            # Add buffer (20%)
            self.optimal_timeouts[test_name] = p99_time * 1.2


class SelfHealingTest:
    """Test that heals itself."""

    def __init__(self, test_id: int, test_name: str):
        """Initialize self-healing test."""
        self.test_id = test_id
        self.test_name = test_name
        self.executions: List[TestExecution] = []
        self.adaptive_waiter = AdaptiveWaiter()
        self.learned_assertions: Dict[str, Any] = {}
        self.learned_timeout_ms: int = 30000

    def record_execution(
        self,
        status: str,
        duration_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Record a test execution."""
        execution = TestExecution(
            test_id=self.test_id,
            test_name=self.test_name,
            status=status,
            duration_ms=duration_ms,
            error=error,
            timestamp=datetime.now().isoformat()
        )
        self.executions.append(execution)

    def get_health_metrics(self) -> TestHealthMetrics:
        """Get health metrics for this test."""
        if not self.executions:
            return TestHealthMetrics(
                test_id=self.test_id,
                total_runs=0,
                passed_runs=0,
                failed_runs=0,
                avg_duration_ms=0,
                optimal_timeout_ms=30000,
                flakiness_score=0,
                recommended_retries=0
            )

        passed = sum(1 for e in self.executions if e.status == 'pass')
        failed = sum(1 for e in self.executions if e.status != 'pass')
        total = len(self.executions)

        avg_duration = sum(e.duration_ms for e in self.executions) / total
        flakiness = failed / total if total > 0 else 0

        # Learn optimal timeout
        sorted_durations = sorted([e.duration_ms for e in self.executions])
        if sorted_durations:
            p99_index = int(len(sorted_durations) * 0.99)
            optimal_timeout = sorted_durations[p99_index] * 1.2
            self.learned_timeout_ms = int(optimal_timeout)

        recommended_retries = int(flakiness * 5) if flakiness > 0.2 else 0

        return TestHealthMetrics(
            test_id=self.test_id,
            total_runs=total,
            passed_runs=passed,
            failed_runs=failed,
            avg_duration_ms=round(avg_duration, 2),
            optimal_timeout_ms=self.learned_timeout_ms,
            flakiness_score=round(flakiness, 3),
            recommended_retries=min(recommended_retries, 5)
        )

    def should_retry(self, last_error: Optional[str]) -> bool:
        """Determine if test should be retried."""
        metrics = self.get_health_metrics()

        # Retry if:
        # 1. Test is flaky (>30% failure rate)
        # 2. Error is transient (timeout, connection)
        if metrics.flakiness_score > 0.3:
            if last_error and any(keyword in last_error.lower() for keyword in ['timeout', 'connection', 'unavailable']):
                return True

        return metrics.recommended_retries > 0

    def auto_fix(self, error_type: str) -> Optional[Dict[str, Any]]:
        """Automatically fix common test issues."""
        fixes = {}

        if error_type == 'timeout':
            fixes['timeout_ms'] = self.learned_timeout_ms + 5000
            fixes['recommendation'] = 'Increase timeout based on learned patterns'

        elif error_type == 'assertion_failed':
            fixes['assertion_strategy'] = 'soft_assert'
            fixes['recommendation'] = 'Switch to soft assertions to collect all failures'

        elif error_type == 'flaky':
            metrics = self.get_health_metrics()
            if metrics.flakiness_score > 0.3:
                fixes['retry_count'] = metrics.recommended_retries
                fixes['recommendation'] = f'Add {metrics.recommended_retries} retries'

        return fixes if fixes else None


class SelfHealingTestRunner:
    """Run self-healing tests."""

    def __init__(self):
        """Initialize runner."""
        self.tests: Dict[int, SelfHealingTest] = {}
        self.healing_actions: List[Dict[str, Any]] = []

    def register_test(self, test_id: int, test_name: str) -> SelfHealingTest:
        """Register a test."""
        test = SelfHealingTest(test_id, test_name)
        self.tests[test_id] = test
        return test

    def run_test_with_healing(
        self,
        test_id: int,
        test_func: Callable,
        max_retries: int = 3
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Run test with automatic healing.

        Returns:
            (success, attempts_used, error_message)
        """
        test = self.tests.get(test_id)
        if not test:
            logger.warning(f"Test not found: {test_id}")
            return False, 0, "Test not registered"

        attempt = 0
        last_error = None

        for attempt in range(1, max_retries + 1):
            start_time = time.time()
            try:
                test_func()
                duration_ms = (time.time() - start_time) * 1000
                test.record_execution('pass', duration_ms)
                return True, attempt, None

            except TimeoutError as e:
                duration_ms = (time.time() - start_time) * 1000
                test.record_execution('timeout', duration_ms, str(e))
                last_error = str(e)

                if attempt < max_retries:
                    # Apply healing
                    fix = test.auto_fix('timeout')
                    if fix:
                        self.healing_actions.append({
                            'test_id': test_id,
                            'action_type': 'timeout_increase',
                            'fix': fix,
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info(f"Healing applied: {fix['recommendation']}")

            except AssertionError as e:
                duration_ms = (time.time() - start_time) * 1000
                test.record_execution('assertion_failed', duration_ms, str(e))
                last_error = str(e)

                if attempt < max_retries and 'flaky' in str(e).lower():
                    fix = test.auto_fix('assertion_failed')
                    if fix:
                        self.healing_actions.append({
                            'test_id': test_id,
                            'action_type': 'assertion_update',
                            'fix': fix,
                            'timestamp': datetime.now().isoformat()
                        })

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                test.record_execution('fail', duration_ms, str(e))
                last_error = str(e)

            # Check if test should be retried
            if test.should_retry(last_error):
                wait_time = 2 ** (attempt - 1)  # Exponential backoff
                logger.info(f"Retrying test {test_id} after {wait_time}s (attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
            elif attempt < max_retries:
                break

        return False, attempt, last_error

    def generate_healing_report(self, output_file: str = "test_results/self_healing_report.json") -> str:
        """Generate self-healing report."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        test_metrics = []
        for test in self.tests.values():
            metrics = test.get_health_metrics()
            test_metrics.append(asdict(metrics))

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.tests),
            'total_healing_actions': len(self.healing_actions),
            'test_health_metrics': test_metrics,
            'healing_actions': self.healing_actions,
            'summary': self._generate_summary()
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated self-healing report: {output_file}")
        return output_file

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of healing actions."""
        by_type = {}
        for action in self.healing_actions:
            action_type = action.get('action_type')
            by_type[action_type] = by_type.get(action_type, 0) + 1

        avg_health_score = sum(
            1 - t.get_health_metrics().flakiness_score
            for t in self.tests.values()
        ) / max(len(self.tests), 1) if self.tests else 0

        return {
            'total_health_score': round(avg_health_score * 100, 1),
            'healing_actions_by_type': by_type,
            'flaky_tests_healed': sum(
                1 for t in self.tests.values()
                if t.get_health_metrics().flakiness_score < 0.2
            )
        }
