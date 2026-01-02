#!/usr/bin/env python3
"""
Test Maintenance Tracking

Tracks test metadata and lifecycle:
- Test ownership
- Creation/modification dates
- Obsolescence detection
- Redundancy identification
- Maintenance metrics

Features:
- Test metadata management
- Obsolete test detection
- Redundant test identification
- Test coverage tracking
- Maintenance reporting
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TestMetadata:
    """Metadata for a test."""
    test_id: int
    test_name: str
    owner: str = "unknown"
    created_date: str = ""
    last_modified_date: str = ""
    last_run_date: Optional[str] = None
    purpose: str = ""
    tags: List[str] = field(default_factory=list)
    related_tests: List[int] = field(default_factory=list)
    status: str = "active"  # active, deprecated, archived
    maintenance_notes: str = ""

    def __post_init__(self):
        if not self.created_date:
            self.created_date = datetime.now().isoformat()
        if not self.last_modified_date:
            self.last_modified_date = datetime.now().isoformat()

    @property
    def age_days(self) -> int:
        """Get age of test in days."""
        created = datetime.fromisoformat(self.created_date)
        return (datetime.now() - created).days

    @property
    def days_since_run(self) -> Optional[int]:
        """Get days since last run."""
        if not self.last_run_date:
            return None
        last_run = datetime.fromisoformat(self.last_run_date)
        return (datetime.now() - last_run).days

    @property
    def is_obsolete(self) -> bool:
        """Determine if test is obsolete."""
        # Test is obsolete if not run in 90 days
        days_since_run = self.days_since_run
        return days_since_run is not None and days_since_run > 90


class TestMaintenanceTracker:
    """Track test maintenance and lifecycle."""

    def __init__(self, metadata_file: str = "testing/test_metadata.json"):
        """Initialize tracker."""
        self.metadata_file = Path(metadata_file)
        self.tests: Dict[int, TestMetadata] = {}
        self.load_metadata()

    def load_metadata(self) -> None:
        """Load test metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    for test_data in data.get('tests', []):
                        test_id = test_data['test_id']
                        self.tests[test_id] = TestMetadata(**test_data)
                logger.info(f"Loaded metadata for {len(self.tests)} tests")
            except Exception as e:
                logger.warning(f"Could not load test metadata: {e}")

    def save_metadata(self) -> None:
        """Save test metadata."""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.tests),
            'tests': [asdict(t) for t in self.tests.values()]
        }

        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved metadata for {len(self.tests)} tests")

    def register_test(self, metadata: TestMetadata) -> None:
        """Register a test with metadata."""
        self.tests[metadata.test_id] = metadata
        logger.info(f"Registered test: {metadata.test_name} (ID: {metadata.test_id})")

    def update_test_run(self, test_id: int) -> None:
        """Update test as having been run."""
        if test_id in self.tests:
            self.tests[test_id].last_run_date = datetime.now().isoformat()

    def mark_test_deprecated(self, test_id: int, reason: str = "") -> None:
        """Mark a test as deprecated."""
        if test_id in self.tests:
            self.tests[test_id].status = 'deprecated'
            self.tests[test_id].maintenance_notes = reason

    def detect_obsolete_tests(self) -> List[TestMetadata]:
        """Detect tests that haven't been run recently."""
        return [t for t in self.tests.values() if t.is_obsolete]

    def detect_redundant_tests(self) -> Dict[str, List[int]]:
        """Detect potentially redundant tests."""
        redundant_groups = defaultdict(list)

        # Group tests by tags
        tag_groups = defaultdict(list)
        for test in self.tests.values():
            for tag in test.tags:
                tag_groups[tag].append(test.test_id)

        # Identify groups with multiple tests
        for tag, test_ids in tag_groups.items():
            if len(test_ids) > 2:
                redundant_groups[f"tag:{tag}"] = test_ids

        return dict(redundant_groups)

    def get_maintenance_metrics(self) -> Dict[str, Any]:
        """Calculate test maintenance metrics."""
        if not self.tests:
            return {'total_tests': 0}

        obsolete = self.detect_obsolete_tests()
        redundant = self.detect_redundant_tests()

        by_owner = defaultdict(int)
        by_status = defaultdict(int)
        by_age = {'0-30_days': 0, '30-90_days': 0, '90+_days': 0}

        for test in self.tests.values():
            by_owner[test.owner] += 1
            by_status[test.status] += 1

            if test.age_days <= 30:
                by_age['0-30_days'] += 1
            elif test.age_days <= 90:
                by_age['30-90_days'] += 1
            else:
                by_age['90+_days'] += 1

        return {
            'total_tests': len(self.tests),
            'by_status': dict(by_status),
            'by_owner': dict(by_owner),
            'by_age': dict(by_age),
            'obsolete_tests': len(obsolete),
            'potentially_redundant_groups': len(redundant),
            'maintenance_health': self._calculate_health_score()
        }

    def _calculate_health_score(self) -> float:
        """Calculate test maintenance health score (0-100)."""
        if not self.tests:
            return 0.0

        score = 100.0

        # Penalize obsolete tests
        obsolete = self.detect_obsolete_tests()
        score -= len(obsolete) * 5

        # Penalize deprecated tests
        deprecated = sum(1 for t in self.tests.values() if t.status == 'deprecated')
        score -= deprecated * 3

        # Penalize untreated redundancy
        redundant = self.detect_redundant_tests()
        score -= len(redundant) * 2

        # Penalize missing metadata
        missing_owner = sum(1 for t in self.tests.values() if t.owner == "unknown")
        score -= missing_owner * 1

        return max(score, 0.0)

    def generate_maintenance_report(
        self,
        output_file: str = "test_results/maintenance_report.json"
    ) -> str:
        """Generate comprehensive maintenance report."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        obsolete_tests = self.detect_obsolete_tests()
        redundant_groups = self.detect_redundant_tests()
        metrics = self.get_maintenance_metrics()

        report = {
            'report_date': datetime.now().isoformat(),
            'metrics': metrics,
            'obsolete_tests': [
                {
                    'test_id': t.test_id,
                    'test_name': t.test_name,
                    'days_since_run': t.days_since_run,
                    'owner': t.owner
                }
                for t in obsolete_tests
            ],
            'potentially_redundant': [
                {
                    'group': group,
                    'test_ids': test_ids,
                    'recommendation': 'Review and consolidate or deprecate'
                }
                for group, test_ids in redundant_groups.items()
            ],
            'recommendations': self._generate_recommendations(
                obsolete_tests, redundant_groups, metrics
            )
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated maintenance report: {output_file}")
        return output_file

    def _generate_recommendations(
        self,
        obsolete: List[TestMetadata],
        redundant: Dict[str, List[int]],
        metrics: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate maintenance recommendations."""
        recommendations = []

        if len(obsolete) > 0:
            recommendations.append({
                'priority': 'high',
                'issue': f'{len(obsolete)} obsolete tests found',
                'action': 'Review and deprecate or remove unused tests',
                'impact': 'Reduces test debt and maintenance burden'
            })

        if len(redundant) > 0:
            recommendations.append({
                'priority': 'medium',
                'issue': f'{len(redundant)} potentially redundant test groups',
                'action': 'Consolidate redundant tests',
                'impact': 'Reduces test suite size and execution time'
            })

        if metrics.get('by_owner', {}).get('unknown', 0) > 10:
            recommendations.append({
                'priority': 'medium',
                'issue': 'Many tests without clear ownership',
                'action': 'Assign owners to unowned tests',
                'impact': 'Improves test maintainability'
            })

        health_score = metrics.get('maintenance_health', 100)
        if health_score < 50:
            recommendations.append({
                'priority': 'critical',
                'issue': f'Test maintenance health score low: {health_score:.0f}/100',
                'action': 'Undertake comprehensive test maintenance pass',
                'impact': 'Improves test reliability and maintainability'
            })

        return recommendations

    def print_summary(self) -> None:
        """Print maintenance summary."""
        metrics = self.get_maintenance_metrics()

        print("\n" + "=" * 80)
        print("TEST MAINTENANCE SUMMARY")
        print("=" * 80)

        print(f"\nTotal Tests: {metrics.get('total_tests', 0)}")
        print(f"Maintenance Health Score: {metrics.get('maintenance_health', 0):.0f}/100")

        print("\nStatus Distribution:")
        for status, count in metrics.get('by_status', {}).items():
            print(f"  {status}: {count}")

        print("\nTest Age Distribution:")
        for age_range, count in metrics.get('by_age', {}).items():
            print(f"  {age_range}: {count}")

        print(f"\nObsolete Tests: {metrics.get('obsolete_tests', 0)}")
        print(f"Potentially Redundant Groups: {metrics.get('potentially_redundant_groups', 0)}")

        print("\n" + "=" * 80)
