"""Repository for writing simple 3-column mapping Excel file."""

from pathlib import Path

from loguru import logger
from openpyxl import Workbook

from app.models.mapping_entry import MappingEntry


class SimpleMappingXlsxRepository:
    """Repository for writing simple VSIC-MCC mapping Excel file."""

    def write(self, entries: list[MappingEntry], output_path: Path) -> None:
        """
        Write mapping entries to simple 3-column Excel file.

        Args:
            entries: List of MappingEntry objects.
            output_path: Path to output Excel file.
        """
        logger.info(
            f"Writing simple mapping file to {output_path} with {len(entries)} entries"
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Mapping"

        # Header
        ws.append(["VSIC", "MCC", "Tên ngành"])

        # Data rows
        for entry in entries:
            vsic_code = entry.vsic_code
            vsic_title = entry.vsic_title

            # Get top-1 MCC or empty string if NO_MATCH
            if entry.top_results:
                mcc_code = entry.top_results[0].mcc_code
            else:
                mcc_code = ""

            ws.append([vsic_code, mcc_code, vsic_title])

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        wb.save(output_path)
        logger.info(f"Successfully wrote simple mapping file to {output_path}")
