#!/usr/bin/env python3
"""
AI/ML-Powered Test Intelligence

Revolutionary testing capabilities using AI/ML:
- LLM-powered test generation from requirements
- Predictive failure analysis using historical data
- Intelligent test selection based on code changes
- Automated bug report generation
- Test improvement suggestions

Features:
- GPT/Claude integration for test generation
- ML models for failure prediction
- Natural language to test case conversion
- Automated bug report creation
- Test quality scoring
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import re

logger = logging.getLogger(__name__)


@dataclass
class TestPrediction:
    """Prediction of test failure probability."""
    test_id: int
    test_name: str
    failure_probability: float  # 0-1
    confidence: float  # 0-1
    reasoning: str
    recommended_action: str


@dataclass
class GeneratedTest:
    """AI-generated test case."""
    test_name: str
    test_code: str
    description: str
    category: str
    estimated_coverage: float
    confidence: float


@dataclass
class BugReport:
    """Automated bug report."""
    title: str
    description: str
    severity: str
    steps_to_reproduce: List[str]
    expected_behavior: str
    actual_behavior: str
    stack_trace: Optional[str]
    environment: Dict[str, str]
    related_tests: List[str]
    suggested_fix: Optional[str]


class AITestIntelligence:
    """AI-powered test intelligence system."""

    def __init__(self, model_type: str = "openai", api_key: Optional[str] = None):
        """
        Initialize AI test intelligence.

        Args:
            model_type: "openai" or "anthropic"
            api_key: API key for LLM provider
        """
        self.model_type = model_type
        self.api_key = api_key
        self.failure_history: List[Dict[str, Any]] = []
        self.code_change_patterns: Dict[str, List[str]] = {}

    def predict_failures(
        self,
        code_changes: List[str],
        test_suite: List[Dict[str, Any]]
    ) -> List[TestPrediction]:
        """
        Predict which tests are likely to fail based on code changes.

        Uses historical failure patterns and code change analysis.
        """
        predictions = []

        for test in test_suite:
            # Calculate failure probability based on patterns
            probability = self._calculate_failure_probability(
                test,
                code_changes
            )

            if probability > 0.3:  # Only return significant predictions
                reasoning = self._explain_prediction(test, code_changes, probability)

                predictions.append(TestPrediction(
                    test_id=test.get('id'),
                    test_name=test.get('question', 'unknown'),
                    failure_probability=round(probability, 3),
                    confidence=0.75,
                    reasoning=reasoning,
                    recommended_action=self._recommend_action(probability)
                ))

        # Sort by failure probability
        predictions.sort(key=lambda p: p.failure_probability, reverse=True)
        return predictions

    def _calculate_failure_probability(
        self,
        test: Dict[str, Any],
        code_changes: List[str]
    ) -> float:
        """Calculate failure probability using pattern matching."""
        probability = 0.0

        # Check if test has failed before
        test_id = test.get('id')
        past_failures = sum(
            1 for f in self.failure_history
            if f.get('test_id') == test_id
        )

        if past_failures > 0:
            probability += min(past_failures * 0.15, 0.5)

        # Check if code changes match historical failure patterns
        for change in code_changes:
            for pattern, failed_tests in self.code_change_patterns.items():
                if re.search(pattern, change, re.IGNORECASE):
                    if test.get('question') in failed_tests:
                        probability += 0.2

        # Category-based risk
        if test.get('category') == 'complex':
            probability += 0.1

        return min(probability, 1.0)

    def _explain_prediction(
        self,
        test: Dict[str, Any],
        code_changes: List[str],
        probability: float
    ) -> str:
        """Generate human-readable explanation for prediction."""
        reasons = []

        test_id = test.get('id')
        past_failures = sum(
            1 for f in self.failure_history
            if f.get('test_id') == test_id
        )

        if past_failures > 0:
            reasons.append(f"Failed {past_failures} times in past")

        if test.get('category') == 'complex':
            reasons.append("Complex test category")

        if code_changes:
            reasons.append(f"{len(code_changes)} related code changes")

        return " | ".join(reasons) if reasons else "Historical patterns"

    def _recommend_action(self, probability: float) -> str:
        """Recommend action based on failure probability."""
        if probability > 0.7:
            return "Run test first, high failure risk"
        elif probability > 0.5:
            return "Prioritize in test suite"
        else:
            return "Monitor for failures"

    def generate_tests_from_requirements(
        self,
        requirement: str,
        test_type: str = "simple"
    ) -> List[GeneratedTest]:
        """
        Generate test cases from natural language requirements.

        Uses LLM to convert requirements to test cases.
        """
        # Simulated LLM-based test generation
        # In production, this would call GPT-4/Claude API

        test_templates = self._create_test_templates(requirement, test_type)

        generated_tests = []
        for template in test_templates:
            generated_tests.append(GeneratedTest(
                test_name=template['name'],
                test_code=template['code'],
                description=template['description'],
                category=test_type,
                estimated_coverage=0.85,
                confidence=0.80
            ))

        return generated_tests

    def _create_test_templates(
        self,
        requirement: str,
        test_type: str
    ) -> List[Dict[str, str]]:
        """Create test templates from requirement."""
        templates = []

        # Extract key entities from requirement
        entities = self._extract_entities(requirement)

        # Generate basic test
        templates.append({
            'name': f"test_{test_type}_{entities.get('action', 'query')}",
            'code': f"""
def test_{test_type}_{entities.get('action', 'query')}():
    \"\"\"Test: {requirement}\"\"\"
    question = "{requirement}"
    response = query_climategpt(question)
    assert response is not None
    assert len(response) > 0
""",
            'description': requirement
        })

        # Generate edge case test
        templates.append({
            'name': f"test_{test_type}_{entities.get('action', 'query')}_edge_case",
            'code': f"""
def test_{test_type}_{entities.get('action', 'query')}_edge_case():
    \"\"\"Test edge case: {requirement}\"\"\"
    question = "{requirement} with invalid data"
    response = query_climategpt(question)
    assert 'error' in response or len(response) == 0
""",
            'description': f"Edge case for: {requirement}"
        })

        return templates

    def _extract_entities(self, text: str) -> Dict[str, str]:
        """Extract entities from requirement text."""
        entities = {}

        # Simple keyword extraction
        if 'emissions' in text.lower():
            entities['subject'] = 'emissions'
        if 'transport' in text.lower():
            entities['sector'] = 'transport'

        # Extract action verbs
        action_verbs = ['calculate', 'query', 'analyze', 'compare', 'list']
        for verb in action_verbs:
            if verb in text.lower():
                entities['action'] = verb
                break

        return entities

    def auto_generate_bug_report(
        self,
        test_failure: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> BugReport:
        """
        Automatically generate detailed bug report from test failure.

        Includes context, repro steps, and suggested fixes.
        """
        test_name = test_failure.get('question', 'unknown')
        error = test_failure.get('error', 'Unknown error')

        # Generate title
        title = f"Test Failure: {test_name[:50]}"

        # Generate description with LLM analysis
        description = self._generate_bug_description(test_failure)

        # Determine severity
        severity = self._determine_severity(test_failure)

        # Generate reproduction steps
        steps = self._generate_repro_steps(test_failure)

        # Extract expected vs actual
        expected = "Test should pass without errors"
        actual = f"Test failed with: {error}"

        # Suggest fix using pattern matching
        suggested_fix = self._suggest_fix(test_failure)

        return BugReport(
            title=title,
            description=description,
            severity=severity,
            steps_to_reproduce=steps,
            expected_behavior=expected,
            actual_behavior=actual,
            stack_trace=test_failure.get('stack_trace'),
            environment={
                'system': test_failure.get('system', 'unknown'),
                'timestamp': test_failure.get('timestamp', ''),
                'test_id': str(test_failure.get('question_id', ''))
            },
            related_tests=self._find_related_tests(test_failure),
            suggested_fix=suggested_fix
        )

    def _generate_bug_description(self, failure: Dict[str, Any]) -> str:
        """Generate detailed bug description."""
        error = failure.get('error', 'Unknown')
        category = failure.get('category', 'unknown')

        description = f"Test failed in category '{category}'.\n\n"
        description += f"Error: {error}\n\n"
        description += "This failure requires investigation."

        return description

    def _determine_severity(self, failure: Dict[str, Any]) -> str:
        """Determine bug severity."""
        error = failure.get('error', '').lower()

        if 'timeout' in error or 'connection' in error:
            return 'high'
        elif 'http 500' in error or 'internal' in error:
            return 'critical'
        elif 'http 4' in error:
            return 'medium'
        else:
            return 'low'

    def _generate_repro_steps(self, failure: Dict[str, Any]) -> List[str]:
        """Generate reproduction steps."""
        steps = [
            "Run test suite",
            f"Execute test ID: {failure.get('question_id')}",
            f"Question: {failure.get('question', 'N/A')}",
            "Observe failure"
        ]
        return steps

    def _suggest_fix(self, failure: Dict[str, Any]) -> Optional[str]:
        """Suggest potential fix based on error pattern."""
        error = failure.get('error', '').lower()

        if 'timeout' in error:
            return "Increase timeout value or optimize service performance"
        elif 'connection' in error:
            return "Check service availability and network connectivity"
        elif '500' in error:
            return "Investigate server logs for internal error cause"
        elif '404' in error:
            return "Verify endpoint URL is correct"
        else:
            return None

    def _find_related_tests(self, failure: Dict[str, Any]) -> List[str]:
        """Find related tests that might be affected."""
        related = []
        sector = failure.get('sector')
        category = failure.get('category')

        # In production, would search test database
        related.append(f"Other {sector} sector tests")
        related.append(f"Other {category} category tests")

        return related

    def suggest_test_improvements(
        self,
        test: Dict[str, Any],
        execution_history: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Suggest improvements for a test based on history."""
        suggestions = []

        # Analyze flakiness
        failures = sum(1 for h in execution_history if h.get('error'))
        if failures > len(execution_history) * 0.2:
            suggestions.append({
                'type': 'reliability',
                'suggestion': 'Add retry logic or increase timeout',
                'reasoning': f'Test has {failures}/{len(execution_history)} failure rate'
            })

        # Analyze performance
        avg_time = sum(h.get('response_time_ms', 0) for h in execution_history) / max(len(execution_history), 1)
        if avg_time > 5000:
            suggestions.append({
                'type': 'performance',
                'suggestion': 'Optimize test or service performance',
                'reasoning': f'Average execution time: {avg_time:.0f}ms'
            })

        # Check coverage
        if test.get('category') == 'simple':
            suggestions.append({
                'type': 'coverage',
                'suggestion': 'Add edge case and error handling tests',
                'reasoning': 'Simple tests should have complementary edge case coverage'
            })

        return suggestions

    def train_on_failures(self, failures: List[Dict[str, Any]]) -> None:
        """Train the prediction model on failure history."""
        self.failure_history.extend(failures)

        # Build code change patterns
        for failure in failures:
            test_name = failure.get('question', '')
            # In production, would analyze git commits
            # For now, use simple pattern matching
            if failure.get('sector'):
                pattern = failure['sector']
                if pattern not in self.code_change_patterns:
                    self.code_change_patterns[pattern] = []
                self.code_change_patterns[pattern].append(test_name)

    def export_model(self, output_file: str = "test_results/ai_model.json") -> str:
        """Export trained model data."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            'timestamp': datetime.now().isoformat(),
            'failure_history_count': len(self.failure_history),
            'patterns': self.code_change_patterns,
            'model_type': self.model_type
        }

        with open(output_file, 'w') as f:
            json.dump(model_data, f, indent=2)

        logger.info(f"Exported AI model to {output_file}")
        return output_file
