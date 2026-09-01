"""Audit result and audit report models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.audit.metrics import AuditStatus, CategoryStatistics, calculate_verified_conversion_rate
from app.core.generators.edge_cases import TestCaseMetadata


@dataclass
class AuditResult:
    """Detailed evaluation result for a single test case."""

    test_id: str
    category: str
    status: AuditStatus
    execution_time_seconds: float
    generated_dfa: Optional[dict] = None
    original_enfa: Optional[dict] = None
    counterexample: Optional[str] = None
    expected_acceptance: Optional[bool] = None
    generated_acceptance: Optional[bool] = None
    states_explored: int = 0
    error_message: Optional[str] = None
    metadata: Optional[TestCaseMetadata] = None
    trace: Optional[List[dict]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert single result to dictionary."""
        return {
            "test_id": self.test_id,
            "category": self.category,
            "status": self.status.value,
            "execution_time_seconds": round(self.execution_time_seconds, 6),
            "generated_dfa": self.generated_dfa,
            "original_enfa": self.original_enfa,
            "counterexample": self.counterexample,
            "expected_acceptance": self.expected_acceptance,
            "generated_acceptance": self.generated_acceptance,
            "states_explored": self.states_explored,
            "error_message": self.error_message,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "trace": self.trace,
        }


@dataclass
class AuditReport:
    """Comprehensive aggregated audit and reliability report."""

    audit_id: str
    transformation: str
    total_tests: int
    verified_count: int
    failed_count: int  # NOT_EQUIVALENT count
    invalid_output_count: int
    execution_error_count: int
    timeout_count: int
    total_execution_time_seconds: float
    results: List[AuditResult] = field(default_factory=list)
    category_statistics: Dict[str, CategoryStatistics] = field(default_factory=dict)
    seed: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def verified_conversion_rate(self) -> Optional[float]:
        """Verified Conversion Rate = verified / (verified + not_equivalent)."""
        return calculate_verified_conversion_rate(self.verified_count, self.failed_count)

    @property
    def average_execution_time_seconds(self) -> float:
        """Average runtime per test case."""
        if self.total_tests == 0:
            return 0.0
        return self.total_execution_time_seconds / self.total_tests

    @property
    def failures(self) -> List[AuditResult]:
        """List of all test results that did not pass verification."""
        return [r for r in self.results if r.status != AuditStatus.VERIFIED]

    @property
    def mathematical_failures(self) -> List[AuditResult]:
        """List of NOT_EQUIVALENT failure cases."""
        return [r for r in self.results if r.status == AuditStatus.NOT_EQUIVALENT]

    @property
    def operational_failures(self) -> List[AuditResult]:
        """List of INVALID_OUTPUT, EXECUTION_ERROR, and TIMEOUT cases."""
        return [r for r in self.results if r.status.is_operational_failure]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete audit report to dictionary."""
        return {
            "audit_id": self.audit_id,
            "transformation": self.transformation,
            "timestamp": self.timestamp,
            "seed": self.seed,
            "summary": {
                "total_tests": self.total_tests,
                "verified_count": self.verified_count,
                "failed_count": self.failed_count,
                "invalid_output_count": self.invalid_output_count,
                "execution_error_count": self.execution_error_count,
                "timeout_count": self.timeout_count,
                "verified_conversion_rate": self.verified_conversion_rate,
                "total_execution_time_seconds": round(self.total_execution_time_seconds, 6),
                "average_execution_time_seconds": round(self.average_execution_time_seconds, 6),
            },
            "category_statistics": {
                cat: stats.to_dict() for cat, stats in sorted(self.category_statistics.items())
            },
            "failures": [f.to_dict() for f in self.failures],
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int | None = None) -> str:
        """Serialize report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
