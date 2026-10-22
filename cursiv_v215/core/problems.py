"""Stable verification findings for code, UI adapters and regression tools.

Codes identify the check, not a substring in a model's prose. A clear assessment
only means these bounded checks found no remaining issue; it is not proof of truth.
"""
from dataclasses import dataclass, asdict
from typing import Literal

Severity = Literal['info', 'warning', 'error']


@dataclass(frozen=True)
class Problem:
    code: str
    severity: Severity
    message: str
    source: str = 'deterministic'

    def record(self) -> dict:
        return asdict(self)


def unique(items: list[Problem]) -> list[Problem]:
    return list(dict.fromkeys(items))
