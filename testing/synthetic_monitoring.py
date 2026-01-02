#!/usr/bin/env python3
"""
Production Synthetic Monitoring

Creates synthetic user journeys that run against production to monitor:
- Real user experience
- Availability and latency
- Error rates
- End-to-end data flows

Features:
- Synthetic transaction execution
- SLI/SLO tracking
- Availability monitoring
- Alert generation
"""

import logging
import json
import requests
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import time

logger = logging.getLogger(__name__)


@dataclass
class SyntheticTransaction:
    """Definition of a synthetic transaction."""
    name: str
    description: str
    steps: List[Dict[str, Any]]  # Steps to execute
    expected_duration_ms: int = 1000
    sla_ms: int = 5000
    critical: bool = False
    schedule: str = "*/5 * * * *"  # Cron schedule


@dataclass
class TransactionResult:
    """Result of synthetic transaction."""
    transaction_name: str
    status: str  # success, failure, timeout
    duration_ms: float
    timestamp: str
    sla_met: bool
    error: Optional[str] = None
    step_results: List[Dict[str, Any]] = None


class SyntheticMonitor:
    """Monitor production with synthetic transactions."""

    def __init__(self, production_url: str = "http://localhost:8010"):
        """Initialize monitor."""
        self.production_url = production_url
        self.transactions: List[SyntheticTransaction] = []
        self.results: List[TransactionResult] = []
        self.sli_targets = {
            'availability': 0.99,  # 99% uptime
            'latency_p95': 2000,   # 95th percentile <= 2s
            'error_rate': 0.01     # Error rate <= 1%
        }

    def register_transaction(self, transaction: SyntheticTransaction) -> None:
        """Register a synthetic transaction."""
        self.transactions.append(transaction)
        logger.info(f"Registered transaction: {transaction.name}")

    def create_health_check_transaction(self) -> SyntheticTransaction:
        """Create basic health check transaction."""
        return SyntheticTransaction(
            name="Health Check",
            description="Basic service health verification",
            steps=[
                {
                    'name': 'call_health_endpoint',
                    'method': 'GET',
                    'endpoint': '/health',
                    'expected_status': 200
                }
            ],
            expected_duration_ms=100,
            sla_ms=500,
            critical=True
        )

    def create_query_transaction(self, question: str) -> SyntheticTransaction:
        """Create query transaction."""
        return SyntheticTransaction(
            name=f"Query: {question[:50]}",
            description=f"Execute climate query: {question}",
            steps=[
                {
                    'name': 'execute_query',
                    'method': 'POST',
                    'endpoint': '/query',
                    'data': {'question': question},
                    'expected_status': 200
                }
            ],
            expected_duration_ms=1000,
            sla_ms=5000,
            critical=True
        )

    def run_transaction(self, transaction: SyntheticTransaction) -> TransactionResult:
        """Run a synthetic transaction."""
        start_time = time.perf_counter()
        step_results = []
        error = None
        status = 'success'

        try:
            for step in transaction.steps:
                step_result = self._execute_step(step)
                step_results.append(step_result)

                if not step_result.get('success'):
                    status = 'failure'
                    error = step_result.get('error')
                    break

        except requests.exceptions.Timeout:
            status = 'timeout'
            error = f"Timeout after {transaction.sla_ms}ms"
        except Exception as e:
            status = 'failure'
            error = str(e)

        duration_ms = (time.perf_counter() - start_time) * 1000
        sla_met = duration_ms <= transaction.sla_ms and status == 'success'

        result = TransactionResult(
            transaction_name=transaction.name,
            status=status,
            duration_ms=round(duration_ms, 2),
            timestamp=datetime.now().isoformat(),
            sla_met=sla_met,
            error=error,
            step_results=step_results
        )

        self.results.append(result)
        self._log_result(result, transaction)

        return result

    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single transaction step."""
        method = step.get('method', 'GET')
        endpoint = step.get('endpoint', '')
        data = step.get('data')
        expected_status = step.get('expected_status', 200)

        url = f"{self.production_url}{endpoint}"

        try:
            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                return {'success': False, 'error': f'Unknown method: {method}'}

            success = response.status_code == expected_status

            return {
                'success': success,
                'status_code': response.status_code,
                'error': None if success else f'Expected {expected_status}, got {response.status_code}'
            }

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _log_result(self, result: TransactionResult, transaction: SyntheticTransaction) -> None:
        """Log transaction result."""
        status_icon = "✓" if result.sla_met else "✗"
        logger.info(
            f"{status_icon} {result.transaction_name}: {result.duration_ms}ms "
            f"(SLA: {transaction.sla_ms}ms, Status: {result.status})"
        )

    def run_all_transactions(self) -> Dict[str, Any]:
        """Run all registered transactions."""
        logger.info(f"Running {len(self.transactions)} synthetic transactions...")

        results = []
        for transaction in self.transactions:
            result = self.run_transaction(transaction)
            results.append(result)

        return self._calculate_metrics(results)

    def _calculate_metrics(self, results: List[TransactionResult]) -> Dict[str, Any]:
        """Calculate SLI/SLO metrics."""
        if not results:
            return {'total': 0}

        successful = sum(1 for r in results if r.status == 'success')
        sla_met = sum(1 for r in results if r.sla_met)
        total_duration = sum(r.duration_ms for r in results)

        availability = successful / len(results) if results else 0
        latencies = sorted([r.duration_ms for r in results if r.status == 'success'])
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0
        error_rate = 1 - (successful / len(results)) if results else 0

        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_transactions': len(results),
            'successful': successful,
            'failed': len(results) - successful,
            'sla_met': sla_met,
            'sli': {
                'availability': round(availability, 3),
                'latency_p95_ms': round(p95_latency, 2),
                'error_rate': round(error_rate, 3)
            },
            'slo': {
                'availability_target': self.sli_targets['availability'],
                'latency_p95_target_ms': self.sli_targets['latency_p95'],
                'error_rate_target': self.sli_targets['error_rate']
            },
            'slo_met': {
                'availability': availability >= self.sli_targets['availability'],
                'latency_p95': p95_latency <= self.sli_targets['latency_p95'],
                'error_rate': error_rate <= self.sli_targets['error_rate']
            },
            'avg_duration_ms': round(total_duration / len(results), 2)
        }

        return metrics

    def generate_monitoring_report(
        self,
        metrics: Dict[str, Any],
        output_file: str = "test_results/synthetic_monitoring.json"
    ) -> str:
        """Generate monitoring report."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            'report_date': datetime.now().isoformat(),
            'metrics': metrics,
            'transactions': [asdict(r) for r in self.results[-20:]],  # Last 20 results
            'alerts': self._generate_alerts(metrics)
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated monitoring report: {output_file}")
        return output_file

    def _generate_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on SLO violations."""
        alerts = []

        slo_met = metrics.get('slo_met', {})

        if not slo_met.get('availability'):
            alerts.append({
                'severity': 'critical',
                'message': f"Availability {metrics['sli']['availability']:.1%} below SLO {self.sli_targets['availability']:.0%}",
                'metric': 'availability'
            })

        if not slo_met.get('latency_p95'):
            alerts.append({
                'severity': 'high',
                'message': f"P95 latency {metrics['sli']['latency_p95_ms']}ms exceeds SLO {self.sli_targets['latency_p95']}ms",
                'metric': 'latency_p95'
            })

        if not slo_met.get('error_rate'):
            alerts.append({
                'severity': 'high',
                'message': f"Error rate {metrics['sli']['error_rate']:.1%} exceeds SLO {self.sli_targets['error_rate']:.1%}",
                'metric': 'error_rate'
            })

        return alerts


def create_default_synthetic_monitor() -> SyntheticMonitor:
    """Create monitor with default transactions."""
    monitor = SyntheticMonitor()

    # Add health check
    monitor.register_transaction(monitor.create_health_check_transaction())

    # Add sample queries
    sample_questions = [
        "What are total greenhouse gas emissions from transportation?",
        "What is the carbon footprint of power generation?",
        "How much methane is emitted from agriculture?",
    ]

    for question in sample_questions:
        monitor.register_transaction(monitor.create_query_transaction(question))

    return monitor
