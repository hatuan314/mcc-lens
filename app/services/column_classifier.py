"""
Column Classifier — classifies OCR lines into MCC table columns.
"""

from app.models.ocr_line import OCRLine


class ColumnClassifier:
    """
    Classifies OCR lines into table columns based on x-position.

    Column thresholds (ratio of image width):
        mcc:      0%  – 12%
        desc:     12% – 46%
        included: 46% – 64%
        similar:  64% – 100%

    Pure function, no state.
    """

    THRESHOLDS: dict[str, tuple[float, float]] = {
        "mcc": (0.0, 0.12),
        "desc": (0.12, 0.46),
        "included": (0.46, 0.64),
        "similar": (0.64, 1.0),
    }

    def classify(self, line: OCRLine, image_width: int) -> str:
        """
        Classify an OCR line into a column based on its x1 position.

        Args:
            line: OCR line with bounding box.
            image_width: Width of the source image in pixels.

        Returns:
            Column name: "mcc", "desc", "included", "similar", or "unknown".
        """
        if image_width <= 0:
            return "unknown"

        x1 = line.bbox[0]
        ratio = x1 / image_width

        for col_name, (low, high) in self.THRESHOLDS.items():
            if low <= ratio < high:
                return col_name

        return "unknown"
