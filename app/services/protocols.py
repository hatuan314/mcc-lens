"""
Protocol interfaces for dependency injection (Surya OCR pipeline).
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Protocol

from PIL import Image

from app.models.mcc_entry import MCCEntry
from app.models.ocr_line import OCRLine
from app.models.vsic_entry import VsicEntry


class OCRService(Protocol):
    """
    Protocol for OCR service that extracts text lines from images (batch processing).
    """

    @abstractmethod
    def extract_lines_batch(self, images: List[Image.Image]) -> List[List[OCRLine]]:
        """
        Extract text lines with pixel bounding boxes from a batch of images.

        Args:
            images: List of PIL Images to process.

        Returns:
            List of OCRLine lists, one per image, each sorted by (round(y1/15), x1).
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


class VsicRepository(Protocol):
    """
    Protocol for reading raw rows from an Excel source.
    """

    @abstractmethod
    def read_rows(self, input_path: Path) -> List[Dict[str, Any]]:
        """
        Read rows from VSIC Excel file.

        Args:
            input_path: Path to the Excel file.

        Returns:
            List of row dictionaries with column headers as keys.
        """
        ...


class VsicWriter(Protocol):
    """
    Protocol for writing VSIC entries to a JSON output.
    """

    @abstractmethod
    def write_entries(self, entries: List[VsicEntry], output_path: Path) -> None:
        """
        Write VSIC entries to JSON file.

        Args:
            entries: List of VsicEntry objects to save.
            output_path: Path to output JSON file.
        """
        ...


class VsicParser(Protocol):
    """
    Protocol for parsing raw Excel rows into VsicEntry objects.
    """

    @abstractmethod
    def parse_rows(self, rows: List[Dict[str, Any]]) -> List[VsicEntry]:
        """
        Parse raw Excel rows into VsicEntry objects.

        Args:
            rows: List of row dictionaries from Excel.

        Returns:
            List of VsicEntry objects with code (string) and digits.
        """
        ...


class EmbeddingClient(Protocol):
    """
    Protocol for generating text embeddings via Ollama.
    """

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each as list of floats).
        """
        ...


class LLMClient(Protocol):
    """
    Protocol for LLM chat completion via Ollama.
    """

    @abstractmethod
    def chat(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        """
        Generate a chat completion with system and user prompts.

        Args:
            system: System prompt for the LLM.
            user: User prompt for the LLM.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            LLM response as string.
        """
        ...


class MappingCheckpointRepository(Protocol):
    """
    Protocol for managing VSIC-to-MCC mapping checkpoint state.
    """

    @abstractmethod
    def load(self) -> Dict[str, Dict]:
        """
        Load completed mapping results from checkpoint.

        Returns:
            Dict mapping VSIC codes to their mapping results.
            Empty dict when no checkpoint exists.
        """
        ...

    @abstractmethod
    def save(self, vsic_code: str, result: Dict) -> None:
        """
        Save a single VSIC mapping result to checkpoint.

        Args:
            vsic_code: VSIC code that was just processed.
            result: Mapping result dict with top_results.
        """
        ...
