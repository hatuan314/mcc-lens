"""
Surya OCR Service implementation.
"""

from typing import List

from loguru import logger
from PIL import Image

from app.models.ocr_line import OCRLine


class SuryaOCRService:
    """
    OCR service using Surya OCR for text line extraction.

    Lazy loads Surya predictors on first use.
    Auto-selects device: MPS → CPU.
    """

    def __init__(self) -> None:
        self._recognition_predictor = None
        self._detection_predictor = None
        self._device: str = ""

    def _ensure_loaded(self) -> None:
        """Lazy load Surya predictors on first use."""
        if self._recognition_predictor is not None:
            return

        logger.info("Loading Surya OCR models (first run downloads ~1-2GB)...")

        try:
            from surya.foundation import FoundationPredictor
            from surya.recognition import RecognitionPredictor
            from surya.detection import DetectionPredictor
        except ImportError as e:
            raise ImportError(
                f"Cannot import surya-ocr: {e}. Install with: pip install surya-ocr"
            ) from e

        # Auto-select device
        self._device = self._auto_device()
        logger.info(f"Using device: {self._device}")

        foundation_predictor = FoundationPredictor()
        self._recognition_predictor = RecognitionPredictor(foundation_predictor)
        self._detection_predictor = DetectionPredictor()

        logger.info("Surya OCR models loaded successfully")

    @staticmethod
    def _auto_device() -> str:
        """Auto-select best available device: MPS → CPU."""
        try:
            import torch

            if torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def extract_lines_batch(self, images: List[Image.Image]) -> List[List[OCRLine]]:
        """
        Extract text lines with pixel bounding boxes from a batch of images.

        Args:
            images: List of PIL Images to process.

        Returns:
            List of OCRLine lists, one per image, each sorted by (round(y1/15), x1).
        """
        self._ensure_loaded()

        predictions = self._recognition_predictor(
            images, det_predictor=self._detection_predictor
        )

        results: List[List[OCRLine]] = []
        for rec in predictions:
            lines: List[OCRLine] = []
            for line in rec.text_lines:
                if not line.text or not line.text.strip():
                    continue
                bbox = list(line.bbox)  # [x1, y1, x2, y2]
                lines.append(
                    OCRLine(
                        text=line.text.strip(),
                        bbox=[
                            float(bbox[0]),
                            float(bbox[1]),
                            float(bbox[2]),
                            float(bbox[3]),
                        ],
                        confidence=(
                            float(line.confidence)
                            if line.confidence is not None
                            else 1.0
                        ),
                    )
                )

            # Sort by y (top to bottom), then x (left to right)
            lines.sort(key=lambda ln: (round(ln.bbox[1] / 15), ln.bbox[0]))
            results.append(lines)

        return results

    def extract_lines(self, image: Image.Image) -> List[OCRLine]:
        """
        Extract text lines with pixel bounding boxes from a single image.

        Convenience method — not part of OCRService Protocol. Use extract_lines_batch for batch processing.

        Args:
            image: PIL Image to process.

        Returns:
            List of OCRLine sorted by (round(y1/15), x1).
        """
        return self.extract_lines_batch([image])[0]
