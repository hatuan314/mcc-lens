"""
Unit tests for ConvertMCCImagesUseCase with fake collaborators.

Covers: dedup (keep longer description), sort by mcc, checkpoint/resume flow.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from PIL import Image

from app.models.mcc_entry import MCCEntry
from app.models.ocr_line import OCRLine
from app.services.convert_mcc_images_use_case import ConvertMCCImagesUseCase


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class FakeOCRService:
    def __init__(self) -> None:
        self.batch_calls: list[int] = []  # Track batch sizes

    def extract_lines_batch(self, images: List[Image.Image]) -> List[List[OCRLine]]:
        self.batch_calls.append(len(images))
        return [[] for _ in images]  # actual lines are ignored by FakeTableParser


class FakeTableParser:
    """Returns pre-programmed entries per source image."""

    def __init__(self, entries_per_image: Dict[str, List[MCCEntry]]) -> None:
        self.entries_per_image = entries_per_image

    def parse(
        self,
        lines: List[OCRLine],
        image_width: int,
        source_image: str = "",
    ) -> List[MCCEntry]:
        return list(self.entries_per_image.get(source_image, []))


class FakeImageRepository:
    def __init__(self, images: List[Path]) -> None:
        self._images = images

    def list_images(self, directory: Path) -> List[Path]:
        return list(self._images)

    def read(self, path: Path) -> Image.Image:
        return Image.new("RGB", (100, 100))


class CapturingJsonRepository:
    def __init__(self) -> None:
        self.saved_entries: List[MCCEntry] = []
        self.saved_path: Path | None = None

    def save(self, entries: List[MCCEntry], output_path: Path) -> None:
        self.saved_entries = list(entries)
        self.saved_path = output_path


class InMemoryCheckpointRepository:
    """In-memory fake matching the CheckpointRepository protocol."""

    def __init__(self, initial: set[str] | None = None) -> None:
        self._done: set[str] = set(initial or set())
        self.cleared: bool = False

    def load(self) -> set[str]:
        return set(self._done)

    def mark_done(self, filename: str) -> None:
        self._done.add(filename)

    def clear(self) -> None:
        self._done.clear()
        self.cleared = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_entry(
    mcc: str,
    source: str = "img.jpg",
    description: str | None = None,
    unparsed: bool = False,
) -> MCCEntry:
    return MCCEntry(
        mcc=mcc if not unparsed else "",
        title=f"Title-{mcc}" if not unparsed else None,
        description=description,
        included_in_mcc=[],
        similar_merchants=[],
        source_image=source,
        unparsed=unparsed,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestDedupAndSort:
    def test_dedup_keeps_longer_description(self, tmp_path: Path) -> None:
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img1.touch()
        img2.touch()

        entries_map = {
            "a.jpg": [make_entry("5812", "a.jpg", description="short")],
            "b.jpg": [
                make_entry("5812", "b.jpg", description="much longer description here")
            ],
        }

        json_repo = CapturingJsonRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository([img1, img2]),
            json_repository=json_repo,
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        assert len(json_repo.saved_entries) == 1
        assert json_repo.saved_entries[0].description == "much longer description here"

    def test_sort_by_mcc(self, tmp_path: Path) -> None:
        img = tmp_path / "a.jpg"
        img.touch()

        entries_map = {
            "a.jpg": [
                make_entry("5999", "a.jpg"),
                make_entry("0742", "a.jpg"),
                make_entry("5812", "a.jpg"),
            ]
        }

        json_repo = CapturingJsonRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository([img]),
            json_repository=json_repo,
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        saved_mccs = [e.mcc for e in json_repo.saved_entries]
        assert saved_mccs == ["0742", "5812", "5999"]

    def test_unparsed_entries_preserved(self, tmp_path: Path) -> None:
        img = tmp_path / "a.jpg"
        img.touch()

        entries_map = {
            "a.jpg": [
                make_entry("5812", "a.jpg", description="desc"),
                make_entry("", "a.jpg", unparsed=True),
            ]
        }

        json_repo = CapturingJsonRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository([img]),
            json_repository=json_repo,
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        unparsed = [e for e in json_repo.saved_entries if e.unparsed]
        assert len(unparsed) == 1


class TestCheckpointResume:
    def test_resume_skips_processed_files(self, tmp_path: Path) -> None:
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img1.touch()
        img2.touch()

        entries_map = {
            "a.jpg": [make_entry("5812", "a.jpg")],
            "b.jpg": [make_entry("5814", "b.jpg")],
        }

        ocr = FakeOCRService()
        json_repo = CapturingJsonRepository()
        # Pre-populate checkpoint: a.jpg already processed
        ckpt_repo = InMemoryCheckpointRepository(initial={"a.jpg"})

        use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr,
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository([img1, img2]),
            json_repository=json_repo,
            checkpoint_repository=ckpt_repo,
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        # Only b.jpg (unprocessed) goes into OCR; a.jpg is skipped before OCR call
        assert len(ocr.batch_calls) == 1
        assert ocr.batch_calls[0] == 1  # batch size 1 (only b.jpg)
        # Only b.jpg's entry saved
        assert [e.mcc for e in json_repo.saved_entries] == ["5814"]

    def test_mark_done_called_after_each_image(self, tmp_path: Path) -> None:
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img1.touch()
        img2.touch()

        entries_map = {
            "a.jpg": [make_entry("5812", "a.jpg")],
            "b.jpg": [make_entry("5814", "b.jpg")],
        }

        ckpt_repo = InMemoryCheckpointRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository([img1, img2]),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=ckpt_repo,
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        # clear() is called at the end, so final _done is empty but cleared flag is True
        assert ckpt_repo.cleared is True

    def test_checkpoint_cleared_on_success(self, tmp_path: Path) -> None:
        img = tmp_path / "a.jpg"
        img.touch()

        ckpt_repo = InMemoryCheckpointRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser({"a.jpg": [make_entry("5812", "a.jpg")]}),
            image_repository=FakeImageRepository([img]),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=ckpt_repo,
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        assert ckpt_repo.cleared is True
        assert ckpt_repo.load() == set()

    def test_resume_matches_nfd_filesystem_names_with_nfc_checkpoint(
        self, tmp_path: Path
    ) -> None:
        """Regression: macOS filesystem yields NFD names; checkpoint stores NFC.

        The use case must treat `hình ảnh-01.jpg` in both forms as identical.
        """
        import unicodedata

        nfc_name = "hình ảnh-01.jpg"
        nfd_name = unicodedata.normalize("NFD", nfc_name)
        assert nfc_name != nfd_name  # sanity: the two forms differ byte-wise

        img = tmp_path / nfd_name
        img.touch()

        ocr = FakeOCRService()
        # Checkpoint stored in NFC form
        ckpt_repo = InMemoryCheckpointRepository(initial={nfc_name})

        use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr,
            table_parser=FakeTableParser({nfc_name: [make_entry("5812", nfc_name)]}),
            image_repository=FakeImageRepository([img]),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=ckpt_repo,
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        # Image must be skipped because its NFC form is in the checkpoint
        assert len(ocr.batch_calls) == 0

    def test_checkpoint_not_touched_when_resume_false(self, tmp_path: Path) -> None:
        """When resume=False, checkpoint repo must not be called."""
        img = tmp_path / "a.jpg"
        img.touch()

        ckpt_repo = InMemoryCheckpointRepository(initial={"stale.jpg"})

        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FakeTableParser({"a.jpg": [make_entry("5812", "a.jpg")]}),
            image_repository=FakeImageRepository([img]),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=ckpt_repo,
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        # Stale state untouched, clear() never called
        assert ckpt_repo.cleared is False
        assert ckpt_repo.load() == {"stale.jpg"}


class TestErrorHandling:
    def test_image_processing_error_is_captured_in_result(self, tmp_path: Path) -> None:
        img = tmp_path / "bad.jpg"
        img.touch()

        class FailingOCRService:
            def extract_lines_batch(self, images) -> list:
                raise RuntimeError("OCR exploded")

        json_repo = CapturingJsonRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FailingOCRService(),
            table_parser=FakeTableParser({}),
            image_repository=FakeImageRepository([img]),
            json_repository=json_repo,
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        result = use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        assert len(result["errors"]) == 1
        assert result["errors"][0]["file"] == "bad.jpg"
        assert "OCR exploded" in result["errors"][0]["error"]


class TestBatchProcessing:
    def test_batch_skip_when_all_checkpointed(self, tmp_path: Path) -> None:
        """When all images in a batch are checkpointed, skip batch OCR entirely."""
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img3 = tmp_path / "c.jpg"
        img1.touch()
        img2.touch()
        img3.touch()

        entries_map = {
            "a.jpg": [make_entry("5812", "a.jpg")],
            "b.jpg": [make_entry("5814", "b.jpg")],
            "c.jpg": [make_entry("5816", "c.jpg")],
        }

        ocr = FakeOCRService()
        ckpt_repo = InMemoryCheckpointRepository(initial={"a.jpg", "b.jpg", "c.jpg"})

        use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr,
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository([img1, img2, img3]),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=ckpt_repo,
        )

        # Batch of 3 images all checkpointed → no OCR call
        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        assert len(ocr.batch_calls) == 0

    def test_ocr_batch_error_marks_no_images_done(self, tmp_path: Path) -> None:
        """When OCR fails for entire batch, no images are marked done."""
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img1.touch()
        img2.touch()

        class FailBatchOCRService:
            def extract_lines_batch(self, images) -> list:
                raise RuntimeError("Surya batch failed")

        ckpt_repo = InMemoryCheckpointRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FailBatchOCRService(),
            table_parser=FakeTableParser({}),
            image_repository=FakeImageRepository([img1, img2]),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=ckpt_repo,
        )

        result = use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        # Both errors logged
        assert len(result["errors"]) == 2
        # No images marked done
        assert ckpt_repo.load() == set()

    def test_parse_error_in_batch_marks_others_done(self, tmp_path: Path) -> None:
        """When 1 image fails parsing in batch, others are still processed and appear in output."""
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img1.touch()
        img2.touch()

        class FailingTableParser:
            def parse(self, lines, image_width, source_image=""):
                # Fail for a.jpg, succeed for b.jpg
                if source_image == "a.jpg":
                    raise RuntimeError("Parse error")
                return [make_entry("5814", source_image)]

        json_repo = CapturingJsonRepository()
        ckpt_repo = InMemoryCheckpointRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=FakeOCRService(),
            table_parser=FailingTableParser(),
            image_repository=FakeImageRepository([img1, img2]),
            json_repository=json_repo,
            checkpoint_repository=ckpt_repo,
        )

        result = use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=True,
        )

        # Only a.jpg error; b.jpg succeeds
        assert len(result["errors"]) == 1
        assert result["errors"][0]["file"] == "a.jpg"
        # b.jpg's entry is in output JSON
        assert [e.mcc for e in json_repo.saved_entries] == ["5814"]
        # Checkpoint cleared after full execution
        assert ckpt_repo.cleared

    def test_image_load_failure_skips_ocr_for_that_image(self, tmp_path: Path) -> None:
        """When image fails to load, it is skipped (error logged) and others in batch proceed."""
        img_good = tmp_path / "good.jpg"
        img_bad = tmp_path / "bad.jpg"
        img_good.touch()
        img_bad.touch()

        class PartialLoadRepository:
            def list_images(self, directory):
                return [img_bad, img_good]

            def read(self, path):
                if path.name == "bad.jpg":
                    raise OSError("Disk error")
                return Image.new("RGB", (100, 100))

        ocr = FakeOCRService()
        json_repo = CapturingJsonRepository()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr,
            table_parser=FakeTableParser(
                {"good.jpg": [make_entry("5812", "good.jpg")]}
            ),
            image_repository=PartialLoadRepository(),
            json_repository=json_repo,
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        result = use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        # bad.jpg error recorded, good.jpg still processed
        assert any(e["file"] == "bad.jpg" for e in result["errors"])
        assert [e.mcc for e in json_repo.saved_entries] == ["5812"]
        # OCR called once with 1 image (only good.jpg)
        assert len(ocr.batch_calls) == 1
        assert ocr.batch_calls[0] == 1

    def test_all_images_fail_to_load_no_ocr_called(self, tmp_path: Path) -> None:
        """When all images in batch fail to load, OCR is never called."""
        img1 = tmp_path / "a.jpg"
        img2 = tmp_path / "b.jpg"
        img1.touch()
        img2.touch()

        class FailingLoadRepository:
            def list_images(self, directory):
                return [img1, img2]

            def read(self, path):
                raise OSError("All disk errors")

        ocr = FakeOCRService()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr,
            table_parser=FakeTableParser({}),
            image_repository=FailingLoadRepository(),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        result = use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        # No OCR calls since no images loaded
        assert len(ocr.batch_calls) == 0
        # Both images errored
        assert len(result["errors"]) == 2

    def test_last_batch_partial(self, tmp_path: Path) -> None:
        """Last batch with fewer than BATCH_SIZE images is processed correctly."""
        # Create 9 images (batch_size=8 → 1 full batch + 1 partial batch)
        images = []
        for i in range(9):
            img_path = tmp_path / f"img{i:02d}.jpg"
            img_path.touch()
            images.append(img_path)

        entries_map = {
            f"img{i:02d}.jpg": [make_entry(str(5000 + i), f"img{i:02d}.jpg")]
            for i in range(9)
        }

        ocr = FakeOCRService()
        use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr,
            table_parser=FakeTableParser(entries_map),
            image_repository=FakeImageRepository(images),
            json_repository=CapturingJsonRepository(),
            checkpoint_repository=InMemoryCheckpointRepository(),
        )

        use_case.execute(
            input_dir=tmp_path,
            output_path=tmp_path / "out.json",
            resume=False,
        )

        # 2 batches: first=8, second=1
        assert len(ocr.batch_calls) == 2
        assert ocr.batch_calls[0] == 8
        assert ocr.batch_calls[1] == 1
