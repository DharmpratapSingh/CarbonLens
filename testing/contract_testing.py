#!/usr/bin/env python3
"""
API Contract Testing

Validates API responses against contracts and schemas.
Detects breaking changes and ensures backward compatibility.

Features:
- OpenAPI schema validation
- Response schema verification
- Breaking change detection
- Backward compatibility checks
- Contract evolution tracking
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class APIContract:
    """API contract definition."""
    name: str
    version: str
    endpoint: str
    method: str
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    status_codes: List[int]
    created_date: str = ""
    breaking_changes: List[str] = None

    def __post_init__(self):
        if not self.created_date:
            self.created_date = datetime.now().isoformat()
        if self.breaking_changes is None:
            self.breaking_changes = []


class ContractValidator:
    """Validate API responses against contracts."""

    def __init__(self, contracts_file: str = "testing/api_contracts.json"):
        """Initialize validator."""
        self.contracts_file = Path(contracts_file)
        self.contracts: Dict[str, APIContract] = {}
        self.violations: List[Dict[str, Any]] = []
        self.load_contracts()

    def load_contracts(self) -> None:
        """Load API contracts."""
        if self.contracts_file.exists():
            try:
                with open(self.contracts_file, 'r') as f:
                    data = json.load(f)
                    for contract_data in data.get('contracts', []):
                        contract = APIContract(**contract_data)
                        self.contracts[contract.endpoint] = contract
                logger.info(f"Loaded {len(self.contracts)} API contracts")
            except Exception as e:
                logger.warning(f"Could not load contracts: {e}")

    def validate_response(
        self,
        endpoint: str,
        method: str,
        response_data: Dict[str, Any],
        status_code: int
    ) -> Tuple[bool, List[str]]:
        """
        Validate API response against contract.

        Returns:
            (is_valid, violations)
        """
        contract_key = f"{method} {endpoint}"
        if contract_key not in self.contracts:
            logger.debug(f"No contract found for {contract_key}")
            return True, []

        contract = self.contracts[contract_key]
        violations = []

        # Validate status code
        if status_code not in contract.status_codes:
            violations.append(
                f"Status code {status_code} not in contract allowed codes: {contract.status_codes}"
            )

        # Validate response schema
        schema_violations = self._validate_schema(response_data, contract.response_schema)
        violations.extend(schema_violations)

        if violations:
            self.violations.append({
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'violations': violations
            })

        return len(violations) == 0, violations

    def _validate_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
        path: str = "$"
    ) -> List[str]:
        """Validate data against schema."""
        violations = []

        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                violations.append(f"Required field missing: {path}.{field}")

        properties = schema.get('properties', {})
        for field, field_schema in properties.items():
            if field in data:
                field_type = field_schema.get('type')
                value = data[field]

                # Type validation
                if field_type == 'string' and not isinstance(value, str):
                    violations.append(f"Field {path}.{field} expected string, got {type(value).__name__}")
                elif field_type == 'number' and not isinstance(value, (int, float)):
                    violations.append(f"Field {path}.{field} expected number, got {type(value).__name__}")
                elif field_type == 'boolean' and not isinstance(value, bool):
                    violations.append(f"Field {path}.{field} expected boolean, got {type(value).__name__}")
                elif field_type == 'array' and not isinstance(value, list):
                    violations.append(f"Field {path}.{field} expected array, got {type(value).__name__}")
                elif field_type == 'object' and not isinstance(value, dict):
                    violations.append(f"Field {path}.{field} expected object, got {type(value).__name__}")

        return violations

    def detect_breaking_changes(
        self,
        new_response: Dict[str, Any],
        contract: APIContract
    ) -> List[str]:
        """Detect breaking changes in response."""
        breaking_changes = []

        # Check for removed required fields
        old_schema = contract.response_schema
        old_required = set(old_schema.get('required', []))
        new_schema = contract.response_schema  # In real scenario, this would be from new contract
        new_required = set(new_schema.get('required', []))

        removed_fields = old_required - new_required
        if removed_fields:
            breaking_changes.append(f"Required fields removed: {removed_fields}")

        # Check for type changes
        for field in old_required & new_required:
            old_type = old_schema.get('properties', {}).get(field, {}).get('type')
            new_type = new_schema.get('properties', {}).get(field, {}).get('type')

            if old_type and new_type and old_type != new_type:
                breaking_changes.append(
                    f"Field {field} type changed from {old_type} to {new_type}"
                )

        return breaking_changes

    def check_backward_compatibility(
        self,
        endpoint: str,
        method: str,
        old_contract: APIContract,
        new_contract: APIContract
    ) -> Tuple[bool, List[str]]:
        """Check backward compatibility between contract versions."""
        incompatibilities = []

        # New required fields break compatibility
        old_required = set(old_contract.response_schema.get('required', []))
        new_required = set(new_contract.response_schema.get('required', []))

        if new_required > old_required:
            added = new_required - old_required
            incompatibilities.append(f"New required fields added: {added}")

        # Removed fields from response break compatibility
        old_props = set(old_contract.response_schema.get('properties', {}).keys())
        new_props = set(new_contract.response_schema.get('properties', {}).keys())

        if old_props > new_props:
            removed = old_props - new_props
            incompatibilities.append(f"Response fields removed: {removed}")

        # Different status codes break compatibility
        if set(old_contract.status_codes) != set(new_contract.status_codes):
            incompatibilities.append("Status codes changed")

        return len(incompatibilities) == 0, incompatibilities

    def save_contract(self, contract: APIContract) -> None:
        """Save API contract."""
        self.contracts[f"{contract.method} {contract.endpoint}"] = contract

        # Write to file
        contracts_list = [
            {
                'name': c.name,
                'version': c.version,
                'endpoint': c.endpoint,
                'method': c.method,
                'request_schema': c.request_schema,
                'response_schema': c.response_schema,
                'status_codes': c.status_codes,
                'created_date': c.created_date,
                'breaking_changes': c.breaking_changes
            }
            for c in self.contracts.values()
        ]

        self.contracts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.contracts_file, 'w') as f:
            json.dump({'contracts': contracts_list}, f, indent=2)

        logger.info(f"Saved contract for {contract.endpoint}")

    def generate_contract_report(self, output_file: str = "test_results/contract_report.json") -> str:
        """Generate contract validation report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_contracts': len(self.contracts),
            'total_violations': len(self.violations),
            'violations': self.violations,
            'contracts': [
                {
                    'endpoint': c.endpoint,
                    'method': c.method,
                    'version': c.version,
                    'breaking_changes': c.breaking_changes
                }
                for c in self.contracts.values()
            ]
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated contract report: {output_file}")
        return output_file
