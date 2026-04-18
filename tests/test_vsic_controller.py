"""
Unit tests for VsicController.

Covers: success (exit 0), FileNotFoundError (exit 1), IO error (exit 2).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from app.controllers.vsic_controller import VsicController
from app.models.vsic_entry import VsicEntry


class FakeExcelRepository:
    def __init__(
        self,
        rows: Optional[List[Dict[str, Any]]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self._rows = rows or []
        self._error = error

    def read_rows(self, input_path: Path) -> List[Dict[str, Any]]:
        if self._error:
            raise self._error
        return self._rows


class FakeJsonRepository:
    def __init__(self, error: Optional[Exception] = None) -> None:
        self._error = error
        self.saved: List[VsicEntry] = []

    def write_entries(self, entries: List[VsicEntry], output_path: Path) -> None:
        if self._error:
            raise self._error
        self.saved = entries


class FakeParserService:
    def parse_rows(self, rows: List[Dict[str, Any]]) -> List[VsicEntry]:
        return [
            VsicEntry(code=str(row.get("code", "1110")), title="Test", digits=4)
            for row in rows
        ]


def _make_controller(excel_repo=None, json_repo=None, parser=None) -> VsicController:
    return VsicController(
        excel_repository=excel_repo or FakeExcelRepository(),
        parser_service=parser or FakeParserService(),
        json_repository=json_repo or FakeJsonRepository(),
    )


class TestVsicControllerExitCodes:
    def test_success_returns_zero(self, tmp_path: Path) -> None:
        controller = _make_controller()
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")
        assert exit_code == 0

    def test_file_not_found_returns_one(self, tmp_path: Path) -> None:
        controller = _make_controller(
            excel_repo=FakeExcelRepository(error=FileNotFoundError("missing"))
        )
        exit_code = controller.execute(tmp_path / "missing.xlsx", tmp_path / "out.json")
        assert exit_code == 1

    def test_io_permission_error_returns_two(self, tmp_path: Path) -> None:
        controller = _make_controller(
            json_repo=FakeJsonRepository(error=OSError("permission denied"))
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")
        assert exit_code == 2

    def test_io_disk_error_returns_two(self, tmp_path: Path) -> None:
        controller = _make_controller(
            json_repo=FakeJsonRepository(error=OSError("disk full"))
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")
        assert exit_code == 2

    def test_generic_exception_returns_one(self, tmp_path: Path) -> None:
        controller = _make_controller(
            excel_repo=FakeExcelRepository(error=ValueError("unexpected"))
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")
        assert exit_code == 1


class TestVsicControllerPipeline:
    def test_entries_passed_to_json_repo(self, tmp_path: Path) -> None:
        rows = [{"code": "1110"}, {"code": "1120"}]
        json_repo = FakeJsonRepository()
        controller = _make_controller(
            excel_repo=FakeExcelRepository(rows=rows),
            json_repo=json_repo,
        )
        controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert len(json_repo.saved) == 2
        assert json_repo.saved[0].digits == 4
