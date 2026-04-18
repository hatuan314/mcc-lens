"""
Unit tests for MCCImageRepository.

Covers: list_images (sorted, filtered by extension, missing dir, not a dir), read.
"""

from pathlib import Path

import pytest
from PIL import Image

from app.repositories.mcc_image_repository import MCCImageRepository


class TestListImages:
    def test_list_images_returns_sorted_jpg_files(self, tmp_path: Path) -> None:
        (tmp_path / "c.jpg").touch()
        (tmp_path / "a.jpg").touch()
        (tmp_path / "b.jpeg").touch()

        repo = MCCImageRepository()
        result = repo.list_images(tmp_path)

        assert [p.name for p in result] == ["a.jpg", "b.jpeg", "c.jpg"]

    def test_list_images_filters_non_image_files(self, tmp_path: Path) -> None:
        (tmp_path / "image.jpg").touch()
        (tmp_path / "notes.txt").touch()
        (tmp_path / "data.json").touch()

        repo = MCCImageRepository()
        result = repo.list_images(tmp_path)

        assert len(result) == 1
        assert result[0].name == "image.jpg"

    def test_list_images_includes_all_supported_extensions(self, tmp_path: Path) -> None:
        for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
            (tmp_path / f"img{ext}").touch()

        repo = MCCImageRepository()
        result = repo.list_images(tmp_path)

        assert len(result) == 6

    def test_list_images_raises_for_missing_directory(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        repo = MCCImageRepository()

        with pytest.raises(FileNotFoundError):
            repo.list_images(missing)

    def test_list_images_raises_for_file_path(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.touch()

        repo = MCCImageRepository()

        with pytest.raises(NotADirectoryError):
            repo.list_images(file_path)

    def test_list_images_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        repo = MCCImageRepository()
        result = repo.list_images(tmp_path)

        assert result == []


class TestReadImage:
    def test_read_returns_pil_image(self, tmp_path: Path) -> None:
        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        img.save(img_path)

        repo = MCCImageRepository()
        result = repo.read(img_path)

        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"

    def test_read_converts_to_rgb(self, tmp_path: Path) -> None:
        img_path = tmp_path / "test.png"
        img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        img.save(img_path)

        repo = MCCImageRepository()
        result = repo.read(img_path)

        assert result.mode == "RGB"
