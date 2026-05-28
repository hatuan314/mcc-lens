"""
Unit tests for VSIC 2025 Excel Repository.
"""

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.repositories.vsic_2025_excel_repository import Vsic2025ExcelRepository


@pytest.fixture
def repository() -> Vsic2025ExcelRepository:
    return Vsic2025ExcelRepository()


class TestValidateHeaders:
    """Tests for _validate_headers method."""

    def test_valid_headers(self, repository: Vsic2025ExcelRepository) -> None:
        headers = ("Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Cấp 5", "Tên ngành")
        result = repository._validate_headers(headers)

        assert result == ["Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Cấp 5", "Tên ngành"]

    def test_minimum_required_headers(
        self, repository: Vsic2025ExcelRepository
    ) -> None:
        """Only Cấp 4, Cấp 5, Tên ngành are required."""
        headers = ("Extra", "Cấp 4", "Cấp 5", "Tên ngành")
        result = repository._validate_headers(headers)

        assert "Cấp 4" in result
        assert "Cấp 5" in result
        assert "Tên ngành" in result

    def test_missing_cap4_raises_value_error(
        self, repository: Vsic2025ExcelRepository
    ) -> None:
        headers = ("Cấp 1", "Cấp 2", "Cấp 3", "Cấp 5", "Tên ngành")

        with pytest.raises(ValueError) as exc_info:
            repository._validate_headers(headers)

        assert "Cấp 4" in str(exc_info.value)

    def test_missing_cap5_raises_value_error(
        self, repository: Vsic2025ExcelRepository
    ) -> None:
        headers = ("Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Tên ngành")

        with pytest.raises(ValueError) as exc_info:
            repository._validate_headers(headers)

        assert "Cấp 5" in str(exc_info.value)

    def test_missing_ten_nganh_raises_value_error(
        self, repository: Vsic2025ExcelRepository
    ) -> None:
        headers = ("Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Cấp 5")

        with pytest.raises(ValueError) as exc_info:
            repository._validate_headers(headers)

        assert "Tên ngành" in str(exc_info.value)

    def test_none_cells_replaced_with_col_index(
        self, repository: Vsic2025ExcelRepository
    ) -> None:
        headers = (None, "Cấp 4", "Cấp 5", "Tên ngành")
        result = repository._validate_headers(headers)

        assert result[0] == "col_0"

    def test_whitespace_stripped(self, repository: Vsic2025ExcelRepository) -> None:
        headers = ("  Cấp 4  ", "  Cấp 5  ", "  Tên ngành  ")
        result = repository._validate_headers(headers)

        assert "Cấp 4" in result
        assert "Cấp 5" in result
        assert "Tên ngành" in result

    def test_multiple_missing_headers(
        self, repository: Vsic2025ExcelRepository
    ) -> None:
        headers = ("Cấp 1", "Cấp 2", "Cấp 3")

        with pytest.raises(ValueError) as exc_info:
            repository._validate_headers(headers)

        error_msg = str(exc_info.value)
        assert "Cấp 4" in error_msg
        assert "Cấp 5" in error_msg
        assert "Tên ngành" in error_msg


class TestReadRows:
    """Tests for read_rows method."""

    def test_file_not_found_raises_error(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        non_existent = tmp_path / "non_existent.xlsx"

        with pytest.raises(FileNotFoundError):
            repository.read_rows(non_existent)

    def test_file_not_found_error_message(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        non_existent = tmp_path / "missing.xlsx"

        with pytest.raises(FileNotFoundError) as exc_info:
            repository.read_rows(non_existent)

        assert "missing.xlsx" in str(exc_info.value)


class TestReadRowsWithMockedWorkbook:
    """Tests using mocked openpyxl workbook."""

    def test_read_rows_with_valid_data(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ("Cấp 4", "Cấp 5", "Tên ngành"),  # Header row
            (111, None, "Trồng lúa"),  # Data row
            (None, 1110, "Lúa hạt"),  # Child row
        ]

        mock_workbook = MagicMock()
        mock_workbook.active = mock_sheet

        test_file = tmp_path / "test.xlsx"
        test_file.touch()

        with patch(
            "app.repositories.vsic_2025_excel_repository.load_workbook"
        ) as mock_load:
            mock_load.return_value = mock_workbook

            rows = repository.read_rows(test_file)

        assert len(rows) == 2
        assert rows[0]["Cấp 4"] == 111
        assert rows[0]["Tên ngành"] == "Trồng lúa"
        assert rows[1]["Cấp 5"] == 1110

    def test_empty_rows_skipped(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ("Cấp 4", "Cấp 5", "Tên ngành"),
            (111, None, "Trồng lúa"),
            (None, None, None),  # Empty row
            (112, None, "Trồng ngô"),
        ]

        mock_workbook = MagicMock()
        mock_workbook.active = mock_sheet

        test_file = tmp_path / "test.xlsx"
        test_file.touch()

        with patch(
            "app.repositories.vsic_2025_excel_repository.load_workbook"
        ) as mock_load:
            mock_load.return_value = mock_workbook

            rows = repository.read_rows(test_file)

        assert len(rows) == 2

    def test_workbook_closed_after_read(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ("Cấp 4", "Cấp 5", "Tên ngành"),
        ]

        mock_workbook = MagicMock()
        mock_workbook.active = mock_sheet

        test_file = tmp_path / "test.xlsx"
        test_file.touch()

        with patch(
            "app.repositories.vsic_2025_excel_repository.load_workbook"
        ) as mock_load:
            mock_load.return_value = mock_workbook

            repository.read_rows(test_file)

        mock_workbook.close.assert_called_once()

    def test_extra_columns_named_with_col_prefix(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ("Cấp 4", "Cấp 5", "Tên ngành"),  # Only 3 headers
            (111, None, "Trồng lúa", "Extra value"),  # 4 values
        ]

        mock_workbook = MagicMock()
        mock_workbook.active = mock_sheet

        test_file = tmp_path / "test.xlsx"
        test_file.touch()

        with patch(
            "app.repositories.vsic_2025_excel_repository.load_workbook"
        ) as mock_load:
            mock_load.return_value = mock_workbook

            rows = repository.read_rows(test_file)

        assert rows[0]["col_3"] == "Extra value"

    def test_invalid_headers_raises_value_error(
        self, repository: Vsic2025ExcelRepository, tmp_path: Path
    ) -> None:
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ("Wrong1", "Wrong2", "Wrong3"),  # Invalid headers
        ]

        mock_workbook = MagicMock()
        mock_workbook.active = mock_sheet

        test_file = tmp_path / "test.xlsx"
        test_file.touch()

        with patch(
            "app.repositories.vsic_2025_excel_repository.load_workbook"
        ) as mock_load:
            mock_load.return_value = mock_workbook

            with pytest.raises(ValueError):
                repository.read_rows(test_file)
