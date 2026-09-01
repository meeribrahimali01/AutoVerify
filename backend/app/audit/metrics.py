"""Audit status classification, metrics, and category statistics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class AuditStatus(str, Enum):
    """Primary classification for an individual test case evaluation."""

    VERIFIED = "VERIFIED"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT = "TIMEOUT"

    @property
    def is_success(self) -> bool:
        """True if the conversion was formally verified as equivalent."""
        return self == AuditStatus.VERIFIED

    @property
    def is_mathematical_failure(self) -> bool:
        """True if the converter produced a valid DFA that failed language equivalence."""
        return self == AuditStatus.NOT_EQUIVALENT

    @property
    def is_operational_failure(self) -> bool:
        """True if the converter crashed, timed out, or produced unparseable output."""
        return self in {
            AuditStatus.INVALID_OUTPUT,
            AuditStatus.EXECUTION_ERROR,
            AuditStatus.TIMEOUT,
        }


@dataclass
class CategoryStatistics:
    """Audit statistics aggregated for a specific test category."""

    category: str
    total: int = 0
    verified: int = 0
    not_equivalent: int = 0
    invalid_output: int = 0
    execution_error: int = 0
    timeout: int = 0

    @property
    def valid_outputs_count(self) -> int:
        """Count of test cases that produced mathematically valid DFAs."""
        return self.verified + self.not_equivalent

    @property
    def verified_conversion_rate(self) -> Optional[float]:
        """Verified Conversion Rate = verified / (verified + not_equivalent).

        Returns None if zero valid DFAs were produced.
        """
        valid = self.valid_outputs_count
        if valid == 0:
            return None
        return self.verified / valid

    def record(self, status: AuditStatus) -> None:
        """Record a single evaluation outcome."""
        self.total += 1
        if status == AuditStatus.VERIFIED:
            self.verified += 1
        elif status == AuditStatus.NOT_EQUIVALENT:
            self.not_equivalent += 1
        elif status == AuditStatus.INVALID_OUTPUT:
            self.invalid_output += 1
        elif status == AuditStatus.EXECUTION_ERROR:
            self.execution_error += 1
        elif status == AuditStatus.TIMEOUT:
            self.timeout += 1

    def to_dict(self) -> dict:
        """Convert statistics to dictionary."""
        return {
            "category": self.category,
            "total": self.total,
            "verified": self.verified,
            "not_equivalent": self.not_equivalent,
            "invalid_output": self.invalid_output,
            "execution_error": self.execution_error,
            "timeout": self.timeout,
            "verified_conversion_rate": self.verified_conversion_rate,
        }


def calculate_verified_conversion_rate(verified: int, not_equivalent: int) -> Optional[float]:
    """Compute overall Verified Conversion Rate: verified / (verified + not_equivalent)."""
    valid = verified + not_equivalent
    if valid == 0:
        return None
    return verified / valid
