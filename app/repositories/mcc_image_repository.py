"""
MCC Image Repository implementation.
"""

from pathlib import Path
from typing import List


class MCCImageRepository:
    """
    Repository for listing image files from a directory.
    """

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    def list_images(self, directory: Path) -> List[Path]:
        """
        List all image files in a directory.

        Args:
            directory: Directory path to search for images.

        Returns:
            List of image file paths, sorted stably.
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        images = []
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                images.append(file_path)

        images.sort(key=lambda p: p.name)
        return images
