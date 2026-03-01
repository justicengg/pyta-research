from __future__ import annotations

from statistics import mean, pstdev


def rule_missing(field: str, value) -> tuple[bool, str]:
    if value is None:
        return True, f'{field} is missing'
    return False, ''


def rule_non_negative(field: str, value) -> tuple[bool, str]:
    if value is None:
        return False, ''
    if value < 0:
        return True, f'{field} is negative'
    return False, ''


def detect_outliers(values: list[float], threshold: float = 3.0) -> list[int]:
    if len(values) < 3:
        return []
    mu = mean(values)
    sigma = pstdev(values)
    if sigma == 0:
        return []
    indexes = []
    for idx, value in enumerate(values):
        z = abs((value - mu) / sigma)
        if z > threshold:
            indexes.append(idx)
    return indexes
