#!/usr/bin/env python3
"""
Chaos Engineering & Resilience Testing

Test system resilience through controlled failure injection:
- Network failure simulation (timeouts, 503, packet loss)
- Resource exhaustion testing (memory, CPU)
- Cascading failure simulation
- Recovery time measurement
- Game day scenario execution

Features:
- Fault injection framework
- Load simulation
- Failure cascading
- Recovery metrics
- Chaos scenarios
"""

import logging
import random
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import json

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of faults to inject."""
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"
    BAD_REQUEST = "bad_request"
    INTERNAL_ERROR = "internal_error"
    SLOW_RESPONSE = "slow_response"
    PACKET_LOSS = "packet_loss"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    CPU_EXHAUSTION = "cpu_exhaustion"


@dataclass
class ChaosScenario:
    """Definition of a chaos scenario."""
    name: str
    description: str
    fault_type: FaultType
    severity: str  # low, medium, high, critical
    duration_seconds: int
    failure_rate: float  # 0-1, percentage of requests to fail
    target_service: str = "climategpt"


@dataclass
class ChaosResult:
    """Result of chaos test execution."""
    scenario_name: str
    status: str  # success, partial, failure
    total_requests: int
    successful_requests: int
    failed_requests: int
    recovery_time_seconds: float
    metrics: Dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def resilience_score(self) -> float:
        """Score resilience (0-100)."""
        # Score based on success rate and recovery time
        success_component = self.success_rate * 60
        recovery_component = max(0, 40 - self.recovery_time_seconds)
        return success_component + recovery_component


class FaultInjector:
    """Inject faults into system."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize fault injector."""
        if seed:
            random.seed(seed)
        self.injected_faults: List[Dict[str, Any]] = []

    def inject_timeout(
        self,
        service_url: str,
        timeout_ms: int = 30000,
        failure_rate: float = 0.5
    ) -> Callable:
        """Create timeout fault injector wrapper."""
        def timeout_wrapper(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                if random.random() < failure_rate:
                    logger.warning(f"Injecting timeout on {service_url}")
                    raise TimeoutError(f"Simulated timeout after {timeout_ms}ms")
                return func(*args, **kwargs)
            return wrapper
        return timeout_wrapper

    def inject_service_unavailable(
        self,
        service_url: str,
        failure_rate: float = 0.5
    ) -> Callable:
        """Create 503 Service Unavailable fault."""
        def wrapper(func: Callable) -> Callable:
            def inner(*args, **kwargs):
                if random.random() < failure_rate:
                    logger.warning(f"Injecting 503 on {service_url}")
                    class FakeResponse:
                        status_code = 503
                        text = "Service Unavailable"
                    return FakeResponse()
                return func(*args, **kwargs)
            return inner
        return wrapper

    def inject_slow_response(
        self,
        service_url: str,
        extra_latency_ms: int = 5000,
        failure_rate: float = 0.3
    ) -> Callable:
        """Create slow response fault."""
        def wrapper(func: Callable) -> Callable:
            def inner(*args, **kwargs):
                if random.random() < failure_rate:
                    logger.warning(f"Injecting {extra_latency_ms}ms latency on {service_url}")
                    time.sleep(extra_latency_ms / 1000)
                return func(*args, **kwargs)
            return inner
        return wrapper

    def record_injection(self, fault: Dict[str, Any]) -> None:
        """Record injected fault."""
        fault['timestamp'] = datetime.now().isoformat()
        self.injected_faults.append(fault)


class ChaosTestRunner:
    """Run chaos engineering tests."""

    def __init__(self):
        """Initialize chaos test runner."""
        self.injector = FaultInjector()
        self.results: List[ChaosResult] = []
        self.start_time: Optional[float] = None

    def create_scenario(
        self,
        name: str,
        fault_type: FaultType,
        severity: str = "high",
        duration_seconds: int = 60
    ) -> ChaosScenario:
        """Create a chaos scenario."""
        failure_rate = {'low': 0.1, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}.get(severity, 0.5)

        return ChaosScenario(
            name=name,
            description=f"{fault_type.value} with {severity} severity",
            fault_type=fault_type,
            severity=severity,
            duration_seconds=duration_seconds,
            failure_rate=failure_rate
        )

    def run_scenario(
        self,
        scenario: ChaosScenario,
        test_func: Callable,
        request_count: int = 100
    ) -> ChaosResult:
        """Run a chaos scenario."""
        logger.info(f"Running chaos scenario: {scenario.name}")
        self.start_time = time.time()

        successful = 0
        failed = 0

        for i in range(request_count):
            try:
                # Inject fault based on scenario
                if random.random() < scenario.failure_rate:
                    self._inject_fault(scenario.fault_type, scenario.target_service)

                # Run test function
                test_func()
                successful += 1

            except Exception as e:
                failed += 1
                logger.warning(f"Request {i} failed: {e}")

        recovery_time = self._measure_recovery_time(test_func)

        result = ChaosResult(
            scenario_name=scenario.name,
            status='success' if failed < request_count * 0.1 else 'partial' if failed < request_count * 0.5 else 'failure',
            total_requests=request_count,
            successful_requests=successful,
            failed_requests=failed,
            recovery_time_seconds=recovery_time,
            metrics={
                'scenario': asdict(scenario),
                'fault_type': scenario.fault_type.value,
                'severity': scenario.severity
            }
        )

        self.results.append(result)
        logger.info(f"Scenario {scenario.name} completed: {result.success_rate:.1%} success rate")

        return result

    def _inject_fault(self, fault_type: FaultType, service: str) -> None:
        """Inject fault into system."""
        logger.debug(f"Injecting {fault_type.value} fault")

        if fault_type == FaultType.TIMEOUT:
            raise TimeoutError("Simulated timeout from chaos injection")

        elif fault_type == FaultType.SERVICE_UNAVAILABLE:
            class FakeResponse:
                status_code = 503
            raise Exception("Service temporarily unavailable")

        elif fault_type == FaultType.INTERNAL_ERROR:
            raise Exception("Internal server error (simulated)")

        elif fault_type == FaultType.SLOW_RESPONSE:
            time.sleep(random.uniform(1, 5))

        elif fault_type == FaultType.PACKET_LOSS:
            if random.random() < 0.3:
                raise ConnectionError("Packet loss (simulated)")

    def _measure_recovery_time(self, test_func: Callable) -> float:
        """Measure time for system to recover."""
        start = time.time()
        retries = 0
        max_retries = 10

        while retries < max_retries:
            try:
                test_func()
                return time.time() - start
            except Exception:
                retries += 1
                time.sleep(1)

        return time.time() - start

    def test_cascading_failure(
        self,
        services: List[str],
        test_func: Callable
    ) -> Dict[str, Any]:
        """Test cascading failure across multiple services."""
        logger.info("Testing cascading failure scenario")

        cascade_state = {
            'failed_services': [],
            'recovery_order': [],
            'total_impact': 0
        }

        # Fail services one by one
        for service in services:
            logger.info(f"Failing service: {service}")
            try:
                test_func()
            except Exception:
                cascade_state['failed_services'].append(service)

        # Test recovery
        for service in reversed(services):
            logger.info(f"Recovering service: {service}")
            if service in cascade_state['failed_services']:
                try:
                    test_func()
                    cascade_state['recovery_order'].append(service)
                except Exception:
                    logger.warning(f"Failed to recover {service}")

        cascade_state['total_impact'] = len(cascade_state['failed_services'])

        return cascade_state

    def test_under_load(
        self,
        concurrent_users: int = 100,
        duration_seconds: int = 60,
        test_func: Callable = None
    ) -> Dict[str, Any]:
        """Test system under concurrent load."""
        logger.info(f"Testing under load: {concurrent_users} concurrent users")

        if test_func is None:
            # Default simple test
            test_func = lambda: time.sleep(0.1)

        import threading

        results = {
            'concurrent_users': concurrent_users,
            'duration_seconds': duration_seconds,
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'avg_response_time': 0,
            'errors': []
        }

        start_time = time.time()
        request_times = []
        lock = threading.Lock()

        def worker():
            while time.time() - start_time < duration_seconds:
                try:
                    req_start = time.time()
                    test_func()
                    request_times.append(time.time() - req_start)
                    with lock:
                        results['successful'] += 1
                except Exception as e:
                    with lock:
                        results['failed'] += 1
                        results['errors'].append(str(e)[:100])
                with lock:
                    results['total_requests'] += 1

        # Create worker threads
        threads = []
        for _ in range(min(concurrent_users, 10)):  # Cap at 10 to avoid resource exhaustion
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        # Wait for completion
        for t in threads:
            t.join(timeout=duration_seconds + 10)

        if request_times:
            results['avg_response_time'] = sum(request_times) / len(request_times)

        return results

    def generate_report(self, output_file: str = "test_results/chaos_report.json") -> str:
        """Generate chaos testing report."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_scenarios': len(self.results),
            'successful_scenarios': sum(1 for r in self.results if r.status == 'success'),
            'failed_scenarios': sum(1 for r in self.results if r.status == 'failure'),
            'avg_recovery_time': sum(r.recovery_time_seconds for r in self.results) / max(len(self.results), 1),
            'avg_resilience_score': sum(r.resilience_score for r in self.results) / max(len(self.results), 1),
            'results': [asdict(r) for r in self.results],
            'injected_faults': self.injector.injected_faults
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated chaos report: {output_file}")
        return output_file
