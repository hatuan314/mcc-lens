"""
Unit tests for ColumnClassifier.
"""

import pytest

from app.models.ocr_line import OCRLine
from app.services.column_classifier import ColumnClassifier


@pytest.fixture
def classifier() -> ColumnClassifier:
    return ColumnClassifier()


def make_line(x1: float, text: str = "foo") -> OCRLine:
    return OCRLine(text=text, bbox=[x1, 0.0, x1 + 10.0, 20.0], confidence=1.0)


class TestColumnClassifierHappyPath:
    """Happy path tests for each column."""

    @pytest.mark.parametrize(
        "x1_ratio,expected",
        [
            (0.05, "mcc"),
            (0.25, "desc"),
            (0.55, "included"),
            (0.80, "similar"),
        ],
    )
    def test_classify_each_column(
        self, classifier: ColumnClassifier, x1_ratio: float, expected: str
    ) -> None:
        image_width = 1000
        line = make_line(x1=image_width * x1_ratio)
        assert classifier.classify(line, image_width) == expected


class TestColumnClassifierBoundaries:
    """Boundary value tests — exact threshold x1 positions."""

    @pytest.mark.parametrize(
        "x1_ratio,expected",
        [
            (0.0, "mcc"),  # lower bound of mcc
            (0.12, "desc"),  # lower bound of desc (half-open)
            (0.46, "included"),  # lower bound of included
            (0.64, "similar"),  # lower bound of similar
            (0.9999, "similar"),  # near upper bound of similar
        ],
    )
    def test_classify_boundaries(
        self, classifier: ColumnClassifier, x1_ratio: float, expected: str
    ) -> None:
        image_width = 1000
        line = make_line(x1=image_width * x1_ratio)
        assert classifier.classify(line, image_width) == expected


class TestColumnClassifierEdgeCases:
    """Edge cases — unknown column, invalid width."""

    def test_zero_width_returns_unknown(self, classifier: ColumnClassifier) -> None:
        line = make_line(x1=100)
        assert classifier.classify(line, image_width=0) == "unknown"

    def test_negative_width_returns_unknown(self, classifier: ColumnClassifier) -> None:
        line = make_line(x1=100)
        assert classifier.classify(line, image_width=-100) == "unknown"

    def test_x1_exceeds_width_returns_unknown(
        self, classifier: ColumnClassifier
    ) -> None:
        line = make_line(x1=1500)
        assert classifier.classify(line, image_width=1000) == "unknown"
