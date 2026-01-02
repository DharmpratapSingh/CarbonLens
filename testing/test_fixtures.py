#!/usr/bin/env python3
"""
Test Fixtures and Mocking Framework

Provides reusable fixtures and mocking utilities for test isolation.
Enables testing without external service dependencies.

Features:
- Mock HTTP responses for ClimateGPT and Llama APIs
- Fixture factories for test data
- Service stubs for offline testing
- Request/response recording and replay
"""

import pytest
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import responses
from unittest.mock import MagicMock, patch


class MockAPIResponses:
    """Mock responses for test APIs."""

    @staticmethod
    def climategpt_success_response(question_id: int = 1) -> Dict[str, Any]:
        """Generate mock ClimateGPT success response."""
        return {
            "answer": f"Transportation emissions in 2023 were 7.2 billion MtCO2 globally.",
            "question_id": question_id,
            "confidence": 0.92,
            "sources": ["IPCC AR6", "WRI Climate Watch"]
        }

    @staticmethod
    def climategpt_error_response(status_code: int = 500) -> Dict[str, Any]:
        """Generate mock ClimateGPT error response."""
        return {
            "error": "Internal server error",
            "status_code": status_code
        }

    @staticmethod
    def llama_success_response(question_id: int = 1) -> Dict[str, Any]:
        """Generate mock Llama success response."""
        return {
            "choices": [{
                "message": {
                    "content": f"Based on available data, transportation contributed approximately 7.2 billion metric tons of CO2 equivalents in 2023."
                }
            }],
            "model": "meta-llama-3.1-8b-instruct",
            "usage": {
                "prompt_tokens": 45,
                "completion_tokens": 28,
                "total_tokens": 73
            }
        }

    @staticmethod
    def llama_error_response() -> Dict[str, Any]:
        """Generate mock Llama error response."""
        return {
            "error": {
                "message": "Model is not loaded",
                "type": "model_not_loaded"
            }
        }


@pytest.fixture
def mock_responses_session():
    """Fixture for mocking all HTTP responses."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_climategpt_api(mock_responses_session):
    """Fixture for mocking ClimateGPT API."""
    def add_mock_response(status=200, body=None, question_id=1):
        if body is None:
            if status == 200:
                body = MockAPIResponses.climategpt_success_response(question_id)
            else:
                body = MockAPIResponses.climategpt_error_response(status)

        mock_responses_session.add(
            responses.POST,
            "http://localhost:8010/query",
            json=body,
            status=status
        )
    return add_mock_response


@pytest.fixture
def mock_llama_api(mock_responses_session):
    """Fixture for mocking Llama API."""
    def add_mock_response(status=200, body=None, question_id=1):
        if body is None:
            if status == 200:
                body = MockAPIResponses.llama_success_response(question_id)
            else:
                body = MockAPIResponses.llama_error_response()

        mock_responses_session.add(
            responses.POST,
            "http://localhost:1234/v1/chat/completions",
            json=body,
            status=status
        )
    return add_mock_response


@pytest.fixture
def test_question():
    """Fixture for test question."""
    return {
        "id": 1,
        "question": "What are the total greenhouse gas emissions from transportation in 2023?",
        "category": "simple",
        "sector": "transport",
        "level": "country",
        "grain": "year",
        "difficulty": "easy"
    }


@pytest.fixture
def test_result_success():
    """Fixture for successful test result."""
    return {
        "question_id": 1,
        "question": "What are total emissions?",
        "category": "simple",
        "sector": "transport",
        "level": "country",
        "grain": "year",
        "difficulty": "easy",
        "system": "climategpt",
        "response": "7.2 billion MtCO2",
        "response_time_ms": 245.5,
        "status_code": 200,
        "error": None,
        "timestamp": "2024-01-15T10:30:00"
    }


@pytest.fixture
def test_result_timeout():
    """Fixture for timeout test result."""
    return {
        "question_id": 1,
        "question": "What are total emissions?",
        "category": "simple",
        "sector": "transport",
        "level": "country",
        "grain": "year",
        "difficulty": "easy",
        "system": "climategpt",
        "response": None,
        "response_time_ms": 31000.0,
        "status_code": None,
        "error": "Timeout after 30s",
        "timestamp": "2024-01-15T10:30:00"
    }


@pytest.fixture
def test_result_error():
    """Fixture for error test result."""
    return {
        "question_id": 1,
        "question": "What are total emissions?",
        "category": "simple",
        "sector": "transport",
        "level": "country",
        "grain": "year",
        "difficulty": "easy",
        "system": "climategpt",
        "response": None,
        "response_time_ms": 150.2,
        "status_code": 500,
        "error": "HTTP 500: Internal Server Error",
        "timestamp": "2024-01-15T10:30:00"
    }


class RequestRecorder:
    """Record and replay HTTP requests for testing."""

    def __init__(self, cassette_dir: str = "test_cassettes"):
        """Initialize request recorder."""
        self.cassette_dir = Path(cassette_dir)
        self.cassette_dir.mkdir(parents=True, exist_ok=True)
        self.recordings = {}

    def load_cassette(self, cassette_name: str) -> List[Dict[str, Any]]:
        """Load recorded requests/responses."""
        cassette_path = self.cassette_dir / f"{cassette_name}.json"
        if cassette_path.exists():
            with open(cassette_path, 'r') as f:
                return json.load(f)
        return []

    def save_cassette(self, cassette_name: str, interactions: List[Dict[str, Any]]) -> None:
        """Save request/response interactions."""
        cassette_path = self.cassette_dir / f"{cassette_name}.json"
        with open(cassette_path, 'w') as f:
            json.dump(interactions, f, indent=2)

    @pytest.fixture
    def record_requests(self):
        """Fixture to record requests."""
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            yield rsps


# Markers for test isolation
def mark_parallel_safe():
    """Mark test as safe for parallel execution."""
    return pytest.mark.parallel_safe


def mark_requires_external_service(service: str):
    """Mark test as requiring external service."""
    return pytest.mark.network(f"requires_{service}")


def mark_flaky(reruns: int = 3):
    """Mark test as flaky with automatic reruns."""
    return pytest.mark.flaky(reruns=reruns)
