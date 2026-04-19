"""
Unit tests for MCCConvertController.

Covers: success (exit 0), FileNotFoundError (exit 1), infrastructure error (exit 2),
IO error (exit 3), generic exception (exit 1).
"""

from pathlib import Path
from typing import List

from PIL import Image

from app.controllers.mcc_convert_controller import MCCConvertController
from app.models.mcc_entry import MCCEntry
from app.models.ocr_line import OCRLine


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class FakeOCRService:
    def extract_lines(self, image: Image.Image) -> List[OCRLine]:
        return []


class FakeTableParser:
    def __init__(self, entries: List[MCCEntry] | None = None) -> None:
        self._entries = entries or []

    def parse(
        self, lines: List[OCRLine], image_width: int, source_image: str = ""
    ) -> List[MCCEntry]:
        return self._entries


class FakeImageRepository:
    def __init__(self, images: List[Path] | None = None) -> None:
        self._images = images or []

    def list_images(self, directory: Path) -> List[Path]:
        return list(self._images)

    def read(self, path: Path) -> Image.Image:
        return Image.new("RGB", (100, 100))


class FakeJsonRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def save(self, entries: List[MCCEntry], output_path: Path) -> None:
        if self._error:
            raise self._error


class FakeCheckpointRepository:
    def load(self) -> set:
        return set()

    def mark_done(self, filename: str) -> None:
        pass

    def clear(self) -> None:
        pass


class RaisingImageRepository:
    """Raises the given exception when list_images is called."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def list_images(self, directory: Path) -> List[Path]:
        raise self._error

    def read(self, path: Path) -> Image.Image:
        return Image.new("RGB", (100, 100))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestMCCConvertControllerExitCodes:
    def _make_controller(
        self,
        image_repo=None,
        json_repo=None,
    ) -> MCCConvertController:
        return MCCConvertController(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser(),
            image_repository=image_repo or FakeImageRepository(),
            json_repository=json_repo or FakeJsonRepository(),
            checkpoint_repository=FakeCheckpointRepository(),
        )

    def test_success_returns_zero(self, tmp_path: Path) -> None:
        controller = self._make_controller()
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 0

    def test_file_not_found_returns_one(self, tmp_path: Path) -> None:
        controller = self._make_controller(
            image_repo=RaisingImageRepository(FileNotFoundError("missing"))
        )
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 1

    def test_infrastructure_error_surya_returns_two(self, tmp_path: Path) -> None:
        controller = self._make_controller(
            image_repo=RaisingImageRepository(
                RuntimeError("surya model failed to load")
            )
        )
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 2

    def test_infrastructure_error_model_returns_two(self, tmp_path: Path) -> None:
        controller = self._make_controller(
            image_repo=RaisingImageRepository(RuntimeError("model weights not found"))
        )
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 2

    def test_io_permission_error_returns_three(self, tmp_path: Path) -> None:
        controller = self._make_controller(
            image_repo=RaisingImageRepository(OSError("permission denied"))
        )
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 3

    def test_io_disk_error_returns_three(self, tmp_path: Path) -> None:
        controller = self._make_controller(
            image_repo=RaisingImageRepository(OSError("disk full"))
        )
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 3

    def test_generic_exception_returns_one(self, tmp_path: Path) -> None:
        controller = self._make_controller(
            image_repo=RaisingImageRepository(ValueError("unexpected value"))
        )
        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 1

    def test_success_with_errors_still_returns_zero(self, tmp_path: Path) -> None:
        """Even when individual images fail, overall exit code is 0."""
        img = tmp_path / "a.jpg"
        img.touch()

        class FailingOCRService:
            def extract_lines(self, image: Image.Image) -> List[OCRLine]:
                raise RuntimeError("OCR failed for this image")

        controller = MCCConvertController(
            ocr_service=FailingOCRService(),
            table_parser=FakeTableParser(),
            image_repository=FakeImageRepository([img]),
            json_repository=FakeJsonRepository(),
            checkpoint_repository=FakeCheckpointRepository(),
        )

        exit_code = controller.execute(tmp_path, tmp_path / "out.json")
        assert exit_code == 0
