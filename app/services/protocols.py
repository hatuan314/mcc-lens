"""
Protocol interfaces for dependency injection (Surya OCR pipeline).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Protocol

from PIL import Image

from app.models.mcc_entry import MCCEntry, SimilarMerchant
from app.models.ocr_line import OCRLine


class OCRService(Protocol):
    """
    Protocol for OCR service that extracts text lines from images.
    """

    @abstractmethod
    def extract_lines(self, image: Image.Image) -> List[OCRLine]:
        """
        Extract text lines with pixel bounding boxes from an image.

        Args:
            image: PIL Image to process.

        Returns:
            List of OCRLine sorted by (round(y1/15), x1).
        """
        ...


class ColumnClassifier(Protocol):
    """
    Protocol for classifying OCR lines into table columns.
    """

    @abstractmethod
    def classify(self, line: OCRLine, image_width: int) -> str:
        """
        Classify an OCR line into a column based on its x-position.

        Args:
            line: OCR line with bounding box.
            image_width: Width of the source image in pixels.

        Returns:
            Column name: "mcc", "desc", "included", "similar", or "unknown".
        """
        ...


class EntryGrouper(Protocol):
    """
    Protocol for grouping classified lines into raw entries.
    """

    @abstractmethod
    def group(self, classified: List[tuple]) -> List[Dict[str, Any]]:
        """
        Group classified lines into raw entries.

        Args:
            classified: List of (OCRLine, column_name) tuples.

        Returns:
            List of raw entry dicts with keys: mcc, _desc_lines, _included_lines, _similar_lines.
        """
        ...


class EntryParser(Protocol):
    """
    Protocol for parsing a raw entry dict into an MCCEntry.
    """

    @abstractmethod
    def parse(self, raw: Dict[str, Any], source_image: str) -> MCCEntry:
        """
        Parse a raw entry dictionary into an MCCEntry.

        Args:
            raw: Raw entry dict from EntryGrouper.
            source_image: Source image filename for tracking.

        Returns:
            MCCEntry object.
        """
        ...


class TableParser(Protocol):
    """
    Protocol for orchestrating the full table parsing pipeline.
    """

    @abstractmethod
    def parse(
        self,
        lines: List[OCRLine],
        image_width: int,
        source_image: str = "",
    ) -> List[MCCEntry]:
        """
        Parse OCR lines into a list of MCCEntry objects.

        Args:
            lines: List of OCRLine from OCRService.
            image_width: Width of the source image in pixels.
            source_image: Source image filename for provenance.

        Returns:
            List of MCCEntry objects.
        """
        ...


class ImageRepository(Protocol):
    """
    Protocol for listing and reading image files from a directory.
    """

    @abstractmethod
    def list_images(self, directory: Path) -> List[Path]:
        """
        List all image files in a directory.

        Args:
            directory: Directory path to search for images.

        Returns:
            List of image file paths, sorted stably.
        """
        ...

    @abstractmethod
    def read(self, path: Path) -> Image.Image:
        """
        Read an image file and return as PIL Image.

        Args:
            path: Path to the image file.

        Returns:
            PIL Image object.
        """
        ...


class JsonRepository(Protocol):
    """
    Protocol for saving MCC entries to JSON file.
    """

    @abstractmethod
    def save(self, entries: List[MCCEntry], output_path: Path) -> None:
        """
        Save MCC entries to JSON file.

        Args:
            entries: List of MCCEntry objects to save.
            output_path: Path to output JSON file.
        """
        ...


class CheckpointRepository(Protocol):
    """
    Protocol for managing checkpoint/resume state.

    The checkpoint file path is encapsulated inside the concrete implementation
    (injected at construction), so the use case does not need to know where
    the checkpoint lives.
    """

    @abstractmethod
    def load(self) -> "set[str]":
        """
        Load the set of already-processed image filenames.

        Returns:
            Set of filenames. Empty set when no checkpoint exists.
        """
        ...

    @abstractmethod
    def mark_done(self, filename: str) -> None:
        """
        Append a filename to the checkpoint and persist immediately.

        Args:
            filename: Image filename that was just processed successfully.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        Delete the checkpoint file after a successful run.
        """
        ...
