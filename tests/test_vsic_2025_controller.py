"""
Unit tests for VSIC 2025 Controller.

Covers: success (exit 0), FileNotFoundError (exit 1), ValueError (exit 1), IO error (exit 2).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from app.controllers.vsic_2025_controller import Vsic2025Controller
from app.models.vsic_2025_entry import Vsic2025Entry, VsicLevel5Child


class FakeExcelRepository:
    """Fake Excel repository for testing."""

    def __init__(
        self,
        rows: Optional[List[Dict[str, Any]]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self._rows = rows or []
        self._error = error
        self.read_path: Optional[Path] = None

    def read_rows(self, input_path: Path) -> List[Dict[str, Any]]:
        self.read_path = input_path
        if self._error:
            raise self._error
        return self._rows


class FakeJsonRepository:
    """Fake JSON repository for testing."""

    def __init__(self, error: Optional[Exception] = None) -> None:
        self._error = error
        self.saved_entries: List[Vsic2025Entry] = []
        self.saved_path: Optional[Path] = None
        self.saved_source: Optional[str] = None

    def write_entries(
        self, entries: List[Vsic2025Entry], output_path: Path, source: str
    ) -> None:
        if self._error:
            raise self._error
        self.saved_entries = entries
        self.saved_path = output_path
        self.saved_source = source


class FakeParserService:
    """Fake parser service for testing."""

    def __init__(
        self, entries: Optional[List[Vsic2025Entry]] = None
    ) -> None:
        self._entries = entries or []
        self.parsed_rows: List[Dict[str, Any]] = []

    def parse_rows(self, rows: List[Dict[str, Any]]) -> List[Vsic2025Entry]:
        self.parsed_rows = rows
        return self._entries


def _make_controller(
    excel_repo: Optional[FakeExcelRepository] = None,
    json_repo: Optional[FakeJsonRepository] = None,
    parser: Optional[FakeParserService] = None,
) -> Vsic2025Controller:
    return Vsic2025Controller(
        excel_repository=excel_repo or FakeExcelRepository(),
        parser_service=parser or FakeParserService(),
        json_repository=json_repo or FakeJsonRepository(),
    )


class TestVsic2025ControllerExitCodes:
    """Tests for exit codes."""

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

    def test_value_error_returns_one(self, tmp_path: Path) -> None:
        """ValueError (e.g., invalid headers) should return exit code 1."""
        controller = _make_controller(
            excel_repo=FakeExcelRepository(
                error=ValueError("Missing required headers")
            )
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert exit_code == 1

    def test_io_permission_error_returns_two(self, tmp_path: Path) -> None:
        controller = _make_controller(
            json_repo=FakeJsonRepository(error=OSError("permission denied"))
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert exit_code == 2

    def test_io_disk_full_error_returns_two(self, tmp_path: Path) -> None:
        controller = _make_controller(
            json_repo=FakeJsonRepository(error=OSError("disk full"))
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert exit_code == 2

    def test_generic_exception_returns_one(self, tmp_path: Path) -> None:
        controller = _make_controller(
            excel_repo=FakeExcelRepository(error=RuntimeError("unexpected"))
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert exit_code == 1


class TestVsic2025ControllerPipeline:
    """Tests for the conversion pipeline."""

    def test_excel_repository_receives_input_path(self, tmp_path: Path) -> None:
        excel_repo = FakeExcelRepository()
        controller = _make_controller(excel_repo=excel_repo)
        input_path = tmp_path / "input.xlsx"

        controller.execute(input_path, tmp_path / "out.json")

        assert excel_repo.read_path == input_path

    def test_parser_receives_rows_from_excel(self, tmp_path: Path) -> None:
        rows = [{"Cấp 4": 111, "Tên ngành": "Test"}]
        excel_repo = FakeExcelRepository(rows=rows)
        parser = FakeParserService()
        controller = _make_controller(excel_repo=excel_repo, parser=parser)

        controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert parser.parsed_rows == rows

    def test_json_repository_receives_entries_from_parser(
        self, tmp_path: Path
    ) -> None:
        entries = [
            Vsic2025Entry(code="111", title="Test", children_level5=[])
        ]
        parser = FakeParserService(entries=entries)
        json_repo = FakeJsonRepository()
        controller = _make_controller(parser=parser, json_repo=json_repo)

        controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert json_repo.saved_entries == entries

    def test_json_repository_receives_output_path(self, tmp_path: Path) -> None:
        json_repo = FakeJsonRepository()
        controller = _make_controller(json_repo=json_repo)
        output_path = tmp_path / "output.json"

        controller.execute(tmp_path / "input.xlsx", output_path)

        assert json_repo.saved_path == output_path

    def test_json_repository_receives_source_as_string(
        self, tmp_path: Path
    ) -> None:
        json_repo = FakeJsonRepository()
        controller = _make_controller(json_repo=json_repo)
        input_path = tmp_path / "vsic-2025.xlsx"

        controller.execute(input_path, tmp_path / "out.json")

        assert json_repo.saved_source == str(input_path)


class TestVsic2025ControllerIntegration:
    """Integration-style tests using real parser service."""

    def test_full_pipeline_with_sample_data(self, tmp_path: Path) -> None:
        from app.services.vsic_2025_parser_service import Vsic2025ParserService

        rows = [
            {"Cấp 4": 111, "Cấp 5": 1110, "Tên ngành": "Trồng lúa"},
            {"Cấp 5": 1111, "Tên ngành": "Lúa gạo"},
            {"Cấp 4": 112, "Tên ngành": "Trồng ngô"},
        ]
        excel_repo = FakeExcelRepository(rows=rows)
        parser = Vsic2025ParserService()
        json_repo = FakeJsonRepository()

        controller = Vsic2025Controller(
            excel_repository=excel_repo,
            parser_service=parser,
            json_repository=json_repo,
        )
        exit_code = controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert exit_code == 0
        assert len(json_repo.saved_entries) == 2
        assert json_repo.saved_entries[0].code == "111"
        assert len(json_repo.saved_entries[0].children_level5) == 2
        assert json_repo.saved_entries[1].code == "112"
        assert json_repo.saved_entries[1].children_level5 == []

    def test_entry_with_inline_child(self, tmp_path: Path) -> None:
        from app.services.vsic_2025_parser_service import Vsic2025ParserService

        rows = [{"Cấp 4": 111, "Cấp 5": 1110, "Tên ngành": "Trồng lúa"}]
        excel_repo = FakeExcelRepository(rows=rows)
        parser = Vsic2025ParserService()
        json_repo = FakeJsonRepository()

        controller = Vsic2025Controller(
            excel_repository=excel_repo,
            parser_service=parser,
            json_repository=json_repo,
        )
        controller.execute(tmp_path / "input.xlsx", tmp_path / "out.json")

        assert len(json_repo.saved_entries) == 1
        assert len(json_repo.saved_entries[0].children_level5) == 1
        assert json_repo.saved_entries[0].children_level5[0].code == "1110"
