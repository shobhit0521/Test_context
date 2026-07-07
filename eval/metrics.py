"""Precision / recall / F1 for a predicted key set against ground truth."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


def score(predicted: set[str], truth: set[str]) -> PRF:
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
