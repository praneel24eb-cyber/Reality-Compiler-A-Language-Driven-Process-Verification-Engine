"""Exact-match set metrics; empty/empty is a perfect match by convention."""

from collections.abc import Hashable, Iterable


def precision_recall(
    predicted: Iterable[Hashable], expected: Iterable[Hashable]
) -> dict[str, float]:
    """Compute micro precision/recall over unique annotated items."""
    actual, gold = set(predicted), set(expected)
    overlap = len(actual & gold)
    return {
        "precision": overlap / len(actual) if actual else float(not gold),
        "recall": overlap / len(gold) if gold else 1.0,
    }
