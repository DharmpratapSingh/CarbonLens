#!/usr/bin/env python3
"""Testing Economics - Cost tracking and ROI calculation."""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EconomicsMetrics:
    """Testing economics metrics."""
    total_cost_usd: float
    cost_per_test_usd: float
    bugs_caught: int
    production_incidents_prevented: int
    roi_percent: float
    payback_period_days: float


class TestingEconomics:
    """Track testing costs and ROI."""

    def __init__(self):
        """Initialize economics tracker."""
        self.test_costs: Dict[str, float] = {}
        self.bugs_caught = 0
        self.incidents_prevented = 0
        self.deployment_cost_per_failure_usd = 1000  # Avg cost of prod failure

    def calculate_cost_per_test(self, test_name: str, cloud_resources_used: Dict[str, float]) -> float:
        """Calculate cloud compute cost per test."""
        # Simple model: $0.0001 per compute minute
        compute_minutes = sum(cloud_resources_used.values())
        cost = compute_minutes * 0.0001
        self.test_costs[test_name] = cost
        return cost

    def calculate_roi(self, test_automation_cost_usd: float, time_period_months: int = 12) -> EconomicsMetrics:
        """Calculate ROI of test automation."""
        total_test_cost = sum(self.test_costs.values())

        # Value calculation
        bugs_value = self.bugs_caught * 500  # Avg cost of bug fix
        incidents_value = self.incidents_prevented * self.deployment_cost_per_failure_usd
        total_value = bugs_value + incidents_value

        # ROI
        net_benefit = total_value - (test_automation_cost_usd + total_test_cost)
        roi_percent = (net_benefit / test_automation_cost_usd * 100) if test_automation_cost_usd > 0 else 0
        payback_days = (test_automation_cost_usd / (total_value / time_period_months * 30)) if total_value > 0 else 999

        return EconomicsMetrics(
            total_cost_usd=total_test_cost,
            cost_per_test_usd=total_test_cost / max(len(self.test_costs), 1),
            bugs_caught=self.bugs_caught,
            production_incidents_prevented=self.incidents_prevented,
            roi_percent=round(roi_percent, 1),
            payback_period_days=round(payback_days, 1)
        )

    def optimize_resource_usage(self) -> Dict[str, str]:
        """Recommend cost optimizations."""
        return {
            'recommendation_1': 'Use spot instances for non-critical tests (50% savings)',
            'recommendation_2': 'Parallelize tests to reduce wall-clock time',
            'recommendation_3': 'Cache test data to reduce I/O costs',
            'recommendation_4': 'Use cheaper regions for dev/staging tests'
        }

    def test_value_score(self, test_name: str, bugs_found: int, execution_cost_usd: float) -> float:
        """Score test value: impact per dollar."""
        if execution_cost_usd == 0:
            return bugs_found * 100
        return (bugs_found * 500) / execution_cost_usd
