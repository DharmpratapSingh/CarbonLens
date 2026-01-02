#!/usr/bin/env python3
"""
Advanced Flaky Test Handling

Identifies, quarantines, and handles flaky tests with:
- Automatic retry with exponential backoff
- Flaky test detection and quarantine
- Test randomization for reproducibility
- Failure pattern analysis

Features:
- Smart retry strategies
- Flaky test quarantine
- Test randomization with seeds
- Failure tracking
"""

import random
import logging
import json
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import time

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy options."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0


@dataclass
class FlakyTestRecord:
    """Record of a flaky test."""
    test_id: int
    test_name: str
    failure_count: int = 0
    success_count: int = 0
    last_status: str = "unknown"  # success, failure, unknown
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None
    runs: List[Dict[str, Any]] = field(default_factory=list)
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def flakiness_score(self) -> float:
        """Calculate flakiness score (0-1)."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.failure_count / total

    @property
    def is_flaky(self) -> bool:
        """Determine if test is flaky."""
        total = self.success_count + self.failure_count
        if total < 3:
            return False
        return self.flakiness_score >= 0.3  # >30% failure rate = flaky


class FlakyTestDetector:
    """Detect and track flaky tests."""

    def __init__(self, flaky_tests_file: str = "test_results/flaky_tests.json"):
        """Initialize detector."""
        self.flaky_tests_file = Path(flaky_tests_file)
        self.flaky_tests: Dict[int, FlakyTestRecord] = {}
        self.load_flaky_tests()

    def load_flaky_tests(self) -> None:
        """Load known flaky tests."""
        if self.flaky_tests_file.exists():
            try:
                with open(self.flaky_tests_file, 'r') as f:
                    data = json.load(f)
                    for test_data in data.get('flaky_tests', []):
                        test_id = test_data['test_id']
                        self.flaky_tests[test_id] = FlakyTestRecord(**test_data)
                logger.info(f"Loaded {len(self.flaky_tests)} known flaky tests")
            except Exception as e:
                logger.warning(f"Could not load flaky tests: {e}")

    def record_result(self, test_id: int, test_name: str, success: bool) -> None:
        """Record test result."""
        if test_id not in self.flaky_tests:
            self.flaky_tests[test_id] = FlakyTestRecord(test_id=test_id, test_name=test_name)

        record = self.flaky_tests[test_id]
        if success:
            record.success_count += 1
            record.last_status = "success"
        else:
            record.failure_count += 1
            record.last_status = "failure"

        record.runs.append({
            'status': record.last_status,
            'timestamp': datetime.now().isoformat()
        })
        record.last_seen = datetime.now().isoformat()

        # Auto-quarantine if detected as flaky
        if record.is_flaky and not record.is_quarantined:
            record.is_quarantined = True
            record.quarantine_reason = f"Flakiness score: {record.flakiness_score:.1%}"
            logger.warning(f"Quarantined flaky test: {test_name} (ID: {test_id})")

    def get_flaky_tests(self) -> List[FlakyTestRecord]:
        """Get all flaky tests."""
        return [t for t in self.flaky_tests.values() if t.is_flaky]

    def get_quarantined_tests(self) -> List[FlakyTestRecord]:
        """Get quarantined tests."""
        return [t for t in self.flaky_tests.values() if t.is_quarantined]

    def save_flaky_tests(self) -> None:
        """Save flaky tests to file."""
        self.flaky_tests_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'timestamp': datetime.now().isoformat(),
            'flaky_tests': [asdict(t) for t in self.flaky_tests.values()],
            'total_flaky': len(self.get_flaky_tests()),
            'total_quarantined': len(self.get_quarantined_tests())
        }
        with open(self.flaky_tests_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved flaky tests to {self.flaky_tests_file}")


class TestRandomizer:
    """Randomize test execution for reproducibility."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize randomizer."""
        self.seed = seed or random.randint(0, 10000)
        random.seed(self.seed)

    def randomize_tests(self, tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Randomize test order."""
        randomized = tests.copy()
        random.shuffle(randomized)
        return randomized

    def get_seed(self) -> int:
        """Get random seed for reproducibility."""
        return self.seed


class SmartRetry:
    """Smart retry mechanism with exponential backoff."""

    def __init__(self, config: RetryConfig = None):
        """Initialize retry handler."""
        self.config = config or RetryConfig()

    def execute_with_retries(
        self,
        func: Callable,
        *args,
        test_id: Optional[int] = None,
        detector: Optional[FlakyTestDetector] = None,
        **kwargs
    ) -> Tuple[Any, bool, int]:
        """
        Execute function with smart retries.

        Returns:
            (result, success, retry_count)
        """
        last_exception = None
        attempt = 0

        for attempt in range(self.config.max_retries):
            try:
                result = func(*args, **kwargs)
                if detector and test_id:
                    detector.record_result(test_id, func.__name__, True)
                return result, True, attempt
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_retries} failed: {e}"
                )

                # Don't sleep after last attempt
                if attempt < self.config.max_retries - 1:
                    delay_ms = self._calculate_delay(attempt)
                    logger.debug(f"Retrying after {delay_ms}ms...")
                    time.sleep(delay_ms / 1000)

        # All retries exhausted
        if detector and test_id:
            detector.record_result(test_id, func.__name__, False)

        return None, False, attempt

    def _calculate_delay(self, attempt: int) -> int:
        """Calculate delay before retry."""
        if self.config.strategy == RetryStrategy.FIXED:
            return self.config.initial_delay_ms

        elif self.config.strategy == RetryStrategy.LINEAR:
            return min(
                self.config.initial_delay_ms * (attempt + 1),
                self.config.max_delay_ms
            )

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = int(
                self.config.initial_delay_ms *
                (self.config.backoff_multiplier ** attempt)
            )
            return min(delay, self.config.max_delay_ms)

        return self.config.initial_delay_ms

    def generate_retry_report(self, detector: FlakyTestDetector) -> Dict[str, Any]:
        """Generate report on retry statistics."""
        flaky = detector.get_flaky_tests()
        quarantined = detector.get_quarantined_tests()

        return {
            'timestamp': datetime.now().isoformat(),
            'retry_config': asdict(self.config),
            'flaky_tests_count': len(flaky),
            'quarantined_tests_count': len(quarantined),
            'flaky_tests': [
                {
                    'test_id': t.test_id,
                    'test_name': t.test_name,
                    'flakiness_score': round(t.flakiness_score, 3),
                    'runs': len(t.runs),
                    'successes': t.success_count,
                    'failures': t.failure_count
                }
                for t in flaky
            ],
            'quarantined_tests': [
                {
                    'test_id': t.test_id,
                    'test_name': t.test_name,
                    'reason': t.quarantine_reason
                }
                for t in quarantined
            ]
        }
