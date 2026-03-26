from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Severity levels used by the audit report."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True)
class Finding:
    """A single audit finding."""

    severity: Severity
    rule_id: str
    message: str
    file_path: str
    element: str | None = None
    component_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AuditReport:
    """Complete audit result for one or more manifest files."""

    manifests: list[str]
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.WARNING)

    @property
    def info(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.INFO)
