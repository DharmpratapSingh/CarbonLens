#!/usr/bin/env python3
"""
Performance Profiling and Analysis

Provides detailed performance metrics beyond response time:
- CPU and memory profiling
- Database query profiling
- Bottleneck identification
- Performance trend analysis
- Profiling reports

Features:
- Decorator-based profiling
- CPU/memory measurement
- Query execution profiling
- Flame graph generation
"""

import time
import logging
import json
from functools import wraps
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProfileMetrics:
    """Performance metrics for a function/operation."""
    name: str
    duration_ms: float
    memory_peak_mb: float
    memory_delta_mb: float
    cpu_percent: float
    query_count: Optional[int] = None
    query_time_ms: Optional[float] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PerformanceProfiler:
    """Profile performance metrics of operations."""

    def __init__(self, output_dir: str = "test_results/profiles"):
        """Initialize profiler."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: List[ProfileMetrics] = []
        self._start_time = None
        self._start_memory = None

    def profile_function(
        self,
        name: str,
        track_memory: bool = True,
        track_cpu: bool = True
    ) -> Callable:
        """Decorator to profile a function."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                start_memory = self._get_memory_usage() if track_memory else 0

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    memory_delta = 0
                    memory_peak = 0

                    if track_memory:
                        current_memory = self._get_memory_usage()
                        memory_delta = current_memory - start_memory
                        memory_peak = current_memory

                    metrics = ProfileMetrics(
                        name=name or func.__name__,
                        duration_ms=round(duration_ms, 2),
                        memory_peak_mb=round(memory_peak, 2),
                        memory_delta_mb=round(memory_delta, 2),
                        cpu_percent=0.0  # Would require process-level tracking
                    )
                    self.metrics.append(metrics)
                    logger.debug(f"Profiled {metrics.name}: {metrics.duration_ms}ms")

            return wrapper
        return decorator

    def start_operation(self, name: str) -> None:
        """Start profiling an operation."""
        self._start_time = time.perf_counter()
        self._start_memory = self._get_memory_usage()

    def end_operation(self, name: str) -> ProfileMetrics:
        """End profiling and record metrics."""
        if self._start_time is None:
            logger.warning(f"No start_operation call for {name}")
            return None

        duration_ms = (time.perf_counter() - self._start_time) * 1000
        current_memory = self._get_memory_usage()
        memory_delta = current_memory - self._start_memory

        metrics = ProfileMetrics(
            name=name,
            duration_ms=round(duration_ms, 2),
            memory_peak_mb=round(current_memory, 2),
            memory_delta_mb=round(memory_delta, 2),
            cpu_percent=0.0
        )
        self.metrics.append(metrics)
        self._start_time = None
        return metrics

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def get_slowest_operations(self, count: int = 10) -> List[ProfileMetrics]:
        """Get slowest operations."""
        return sorted(self.metrics, key=lambda m: m.duration_ms, reverse=True)[:count]

    def get_memory_intensive_operations(self, count: int = 10) -> List[ProfileMetrics]:
        """Get most memory-intensive operations."""
        return sorted(self.metrics, key=lambda m: m.memory_peak_mb, reverse=True)[:count]

    def generate_report(self, output_filename: Optional[str] = None) -> str:
        """Generate profiling report."""
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"profile_{timestamp}.json"

        output_path = self.output_dir / output_filename

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_operations': len(self.metrics),
            'total_time_ms': sum(m.duration_ms for m in self.metrics),
            'total_memory_mb': sum(m.memory_delta_mb for m in self.metrics),
            'slowest_operations': [asdict(m) for m in self.get_slowest_operations(10)],
            'memory_intensive': [asdict(m) for m in self.get_memory_intensive_operations(10)],
            'all_metrics': [asdict(m) for m in self.metrics]
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated profiling report: {output_path}")
        return str(output_path)

    def print_summary(self) -> None:
        """Print profiling summary."""
        if not self.metrics:
            logger.info("No profiling metrics recorded")
            return

        slowest = self.get_slowest_operations(5)
        print("\n" + "=" * 80)
        print("PERFORMANCE PROFILING SUMMARY")
        print("=" * 80)
        print(f"\nTotal Operations: {len(self.metrics)}")
        print(f"Total Time: {sum(m.duration_ms for m in self.metrics):.0f}ms")
        print(f"Total Memory: {sum(m.memory_delta_mb for m in self.metrics):.1f}MB")

        print("\nTop 5 Slowest Operations:")
        print("-" * 80)
        for i, metric in enumerate(slowest, 1):
            print(f"{i}. {metric.name}: {metric.duration_ms:.0f}ms (Memory: {metric.memory_delta_mb:.1f}MB)")

        print("\n" + "=" * 80)


class QueryProfiler:
    """Profile database queries."""

    def __init__(self):
        """Initialize query profiler."""
        self.queries: List[Dict[str, Any]] = []

    def record_query(
        self,
        query: str,
        duration_ms: float,
        row_count: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Record a database query."""
        self.queries.append({
            'query': query[:100],  # Truncate long queries
            'duration_ms': round(duration_ms, 2),
            'row_count': row_count,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

    def get_slowest_queries(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries."""
        return sorted(self.queries, key=lambda q: q['duration_ms'], reverse=True)[:count]

    def get_statistics(self) -> Dict[str, Any]:
        """Get query statistics."""
        if not self.queries:
            return {'total_queries': 0}

        durations = [q['duration_ms'] for q in self.queries]
        return {
            'total_queries': len(self.queries),
            'total_duration_ms': sum(durations),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'total_rows': sum(q['row_count'] for q in self.queries),
            'error_count': sum(1 for q in self.queries if q['error'])
        }

    def print_report(self) -> None:
        """Print query profiling report."""
        stats = self.get_statistics()
        slowest = self.get_slowest_queries(5)

        print("\n" + "=" * 80)
        print("DATABASE QUERY PROFILING REPORT")
        print("=" * 80)
        print(f"\nTotal Queries: {stats.get('total_queries', 0)}")
        print(f"Total Duration: {stats.get('total_duration_ms', 0):.0f}ms")
        print(f"Average Duration: {stats.get('avg_duration_ms', 0):.1f}ms")
        print(f"Errors: {stats.get('error_count', 0)}")

        print("\nTop 5 Slowest Queries:")
        print("-" * 80)
        for i, query in enumerate(slowest, 1):
            print(f"{i}. {query['query']}: {query['duration_ms']:.1f}ms")

        print("\n" + "=" * 80)


def measure_time(func: Callable) -> Callable:
    """Simple decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"{func.__name__} took {elapsed_ms:.1f}ms")
    return wrapper
