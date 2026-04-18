"""
OCR Line model for Surya OCR output.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OCRLine:
    """
    Dataclass representing a single OCR line with pixel bounding box.

    Attributes:
        text: Extracted text content.
        bbox: Bounding box as [x1, y1, x2, y2] in pixel coordinates.
        confidence: Recognition confidence score (0.0–1.0).
    """

    text: str
    bbox: list[float]
    confidence: float = 0.0
