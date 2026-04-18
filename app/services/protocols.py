"""
Protocol interfaces for dependency injection.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Protocol, Tuple

from PIL import Image

from app.models.mcc_entry import BBoxTextItem, MCCEntry


class VisionService(Protocol):
    """
    Protocol for vision/OCR service that extracts text regions from images.
    """

    @abstractmethod
    def extract_regions(self, image_path: Path) -> List[BBoxTextItem]:
        """
        Extract text regions with bounding boxes from an image.

        Args:
            image_path: Path to the image file.

        Returns:
            List of BBoxTextItem with text and normalized bbox coordinates.
        """
        ...


class TableReconstructor(Protocol):
    """
    Protocol for reconstructing table structure from text regions.
    """

    @abstractmethod
    def reconstruct(
        self, regions: List[BBoxTextItem], image_size: Tuple[int, int]
    ) -> List[Dict[str, str]]:
        """
        Reconstruct table rows from OCR regions.

        Args:
            regions: List of text regions with bounding boxes.
            image_size: Tuple of (width, height) of the original image.

        Returns:
            List of row dictionaries with keys: mcc, title_description, included, similar_merchants.
        """
        ...

    @abstractmethod
    def visualize_results(
        self, image_path: Path, rows: List[Dict[str, str]]
    ) -> Image.Image:
        """
        Visualize reconstructed table on image.

        Args:
            image_path: Path to the original image.
            rows: Reconstructed table rows.

        Returns:
            PIL Image with bounding boxes and labels drawn.
        """
        ...


class MCCParser(Protocol):
    """
    Protocol for parsing reconstructed table rows into MCCEntry objects.
    """

    @abstractmethod
    def parse(self, rows: List[Dict[str, str]], source: str) -> List[MCCEntry]:
        """
        Parse table rows into MCCEntry objects.

        Args:
            rows: List of row dictionaries from table reconstruction.
            source: Source filename for tracking.

        Returns:
            List of MCCEntry objects.
        """
        ...


class ImageRepository(Protocol):
    """
    Protocol for listing image files from a directory.
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
    """

    @abstractmethod
    def load(self, checkpoint_path: Path) -> Dict[str, Any]:
        """
        Load checkpoint state.

        Args:
            checkpoint_path: Path to checkpoint file.

        Returns:
            Dictionary with checkpoint state.
        """
        ...

    @abstractmethod
    def save(self, checkpoint_path: Path, state: Dict[str, Any]) -> None:
        """
        Save checkpoint state.

        Args:
            checkpoint_path: Path to checkpoint file.
            state: Dictionary with checkpoint state to save.
        """
        ...

    @abstractmethod
    def exists(self, checkpoint_path: Path) -> bool:
        """
        Check if checkpoint file exists.

        Args:
            checkpoint_path: Path to checkpoint file.

        Returns:
            True if checkpoint exists, False otherwise.
        """
        ...
