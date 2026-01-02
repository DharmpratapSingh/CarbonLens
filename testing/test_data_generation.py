#!/usr/bin/env python3
"""
Test Data Generation

Generates test data dynamically using:
- Parameterized test generation
- Property-based testing with Hypothesis
- Edge case generation
- Mutation testing

Features:
- Automatic test data generation
- Edge case and boundary testing
- Property-based testing integration
- Data variation generation
"""

import logging
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import random
import string

logger = logging.getLogger(__name__)


class TestDataGenerator:
    """Generate test data dynamically."""

    @staticmethod
    def generate_questions(
        count: int = 10,
        sectors: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        difficulty_levels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Generate test questions with variations."""
        if sectors is None:
            sectors = [
                "transport", "power", "waste", "agriculture",
                "buildings", "industrial"
            ]
        if categories is None:
            categories = ["simple", "temporal", "comparative", "complex"]
        if difficulty_levels is None:
            difficulty_levels = ["easy", "medium", "hard"]

        questions = []
        base_templates = [
            "What are the total {sector} emissions for {year}?",
            "How much {sector} emissions did {location} produce in {year}?",
            "Compare {sector} emissions between {location1} and {location2}",
            "What is the trend in {sector} emissions from {year1} to {year2}?",
        ]

        for i in range(count):
            sector = random.choice(sectors)
            category = random.choice(categories)
            difficulty = random.choice(difficulty_levels)
            year = random.randint(2015, 2023)
            location = random.choice(["USA", "China", "India", "EU", "Japan"])

            template = random.choice(base_templates)
            question_text = template.format(
                sector=sector,
                year=year,
                location=location,
                location1=location,
                location2=random.choice(["USA", "China", "India", "EU", "Japan"]),
                year1=year - 5,
                year2=year
            )

            questions.append({
                'id': i + 1,
                'question': question_text,
                'category': category,
                'sector': sector,
                'level': random.choice(['country', 'state', 'city']),
                'grain': random.choice(['year', 'month']),
                'difficulty': difficulty
            })

        return questions

    @staticmethod
    def generate_edge_cases() -> List[Dict[str, Any]]:
        """Generate edge case test questions."""
        edge_cases = [
            {
                'id': 1,
                'question': '',  # Empty question
                'category': 'edge',
                'expected_behavior': 'should return error'
            },
            {
                'id': 2,
                'question': 'x' * 10000,  # Very long question
                'category': 'edge',
                'expected_behavior': 'should handle or truncate'
            },
            {
                'id': 3,
                'question': '!!!###$$$%%%',  # Special characters
                'category': 'edge',
                'expected_behavior': 'should handle gracefully'
            },
            {
                'id': 4,
                'question': 'What are emissions in year 9999?',  # Future year
                'category': 'edge',
                'expected_behavior': 'should indicate no data available'
            },
            {
                'id': 5,
                'question': 'What are emissions in year 1900?',  # Historical
                'category': 'edge',
                'expected_behavior': 'should indicate no data available'
            },
            {
                'id': 6,
                'question': 'µ ñ ü ß 中文',  # Non-ASCII characters
                'category': 'edge',
                'expected_behavior': 'should handle unicode'
            },
        ]
        return edge_cases

    @staticmethod
    def generate_boundary_values() -> List[Dict[str, Any]]:
        """Generate boundary value test cases."""
        boundaries = [
            {'value': 0, 'description': 'zero emissions'},
            {'value': 1, 'description': 'single unit'},
            {'value': 999999999, 'description': 'very large number'},
            {'value': -1, 'description': 'negative number'},
            {'value': 0.0001, 'description': 'very small decimal'},
            {'value': None, 'description': 'null value'},
        ]
        return boundaries

    @staticmethod
    def mutate_question(question: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate mutations of a test question."""
        mutations = [question.copy()]

        # Mutation 1: Typo
        mutated = question.copy()
        words = mutated['question'].split()
        if words:
            word = words[0]
            if len(word) > 2:
                mutated['question'] = mutated['question'].replace(
                    word,
                    word[:-1] + random.choice(string.ascii_letters)
                )
            mutations.append(mutated)

        # Mutation 2: Different tense
        mutated = question.copy()
        mutated['question'] = mutated['question'].replace(
            'are the',
            'were the'
        )
        mutations.append(mutated)

        # Mutation 3: Different quantity
        mutated = question.copy()
        if any(char.isdigit() for char in mutated['question']):
            mutated['question'] = mutated['question'] + ' vs previous year'
        mutations.append(mutated)

        return [m for m in mutations if m != question]

    @staticmethod
    def parameterize_test(
        test_func: Callable,
        parameters: List[Dict[str, Any]]
    ) -> List[Callable]:
        """Generate parameterized test functions."""
        test_variants = []

        for param_set in parameters:
            def parameterized_test(params=param_set):
                return test_func(**params)

            test_variants.append(parameterized_test)

        return test_variants


class HypothesisTestGenerator:
    """Generate property-based tests using Hypothesis."""

    @staticmethod
    def generate_property_tests() -> List[Dict[str, Any]]:
        """Generate property-based test strategies."""
        try:
            from hypothesis import strategies as st

            strategies = [
                {
                    'name': 'question_text',
                    'strategy': st.text(
                        alphabet=string.ascii_letters + ' ',
                        min_size=5,
                        max_size=200
                    ),
                    'property': 'Non-empty valid question text'
                },
                {
                    'name': 'year',
                    'strategy': st.integers(min_value=2000, max_value=2030),
                    'property': 'Valid year range'
                },
                {
                    'name': 'emissions_value',
                    'strategy': st.floats(
                        min_value=0,
                        max_value=1e12,
                        allow_nan=False,
                        allow_infinity=False
                    ),
                    'property': 'Non-negative emissions value'
                },
                {
                    'name': 'location',
                    'strategy': st.sampled_from(['USA', 'China', 'EU', 'Japan', 'India']),
                    'property': 'Valid location'
                }
            ]
            return strategies
        except ImportError:
            logger.warning("Hypothesis not installed, skipping property-based tests")
            return []


class TestDataValidator:
    """Validate generated test data."""

    @staticmethod
    def validate_question(question: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate a test question."""
        errors = []

        # Required fields
        required_fields = ['id', 'question', 'category', 'sector', 'level', 'grain', 'difficulty']
        for field in required_fields:
            if field not in question:
                errors.append(f"Missing required field: {field}")

        # Field value validation
        if 'question' in question:
            if not isinstance(question['question'], str):
                errors.append("Question must be a string")
            if len(question['question']) < 5:
                errors.append("Question too short (min 5 chars)")
            if len(question['question']) > 500:
                errors.append("Question too long (max 500 chars)")

        if 'category' in question:
            valid_categories = ['simple', 'temporal', 'comparative', 'complex']
            if question['category'] not in valid_categories:
                errors.append(f"Invalid category: {question['category']}")

        if 'difficulty' in question:
            valid_difficulties = ['easy', 'medium', 'hard']
            if question['difficulty'] not in valid_difficulties:
                errors.append(f"Invalid difficulty: {question['difficulty']}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_question_bank(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate entire question bank."""
        results = {
            'total_questions': len(questions),
            'valid_questions': 0,
            'invalid_questions': 0,
            'coverage': {},
            'errors': []
        }

        category_coverage = {}
        sector_coverage = {}

        for question in questions:
            is_valid, errors = TestDataValidator.validate_question(question)
            if is_valid:
                results['valid_questions'] += 1
                category = question.get('category')
                sector = question.get('sector')
                category_coverage[category] = category_coverage.get(category, 0) + 1
                sector_coverage[sector] = sector_coverage.get(sector, 0) + 1
            else:
                results['invalid_questions'] += 1
                results['errors'].extend(errors)

        results['coverage'] = {
            'by_category': category_coverage,
            'by_sector': sector_coverage
        }

        return results
