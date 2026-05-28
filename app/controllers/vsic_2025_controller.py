"""
VSIC 2025 Convert Controller.
"""

from pathlib import Path
from typing import List

from loguru import logger

from app.models.vsic_2025_entry import Vsic2025Entry
from app.repositories.vsic_2025_excel_repository import Vsic2025ExcelRepository
from app.repositories.vsic_2025_json_repository import Vsic2025JsonRepository
from app.services.vsic_2025_parser_service import Vsic2025ParserService


class Vsic2025Controller:
    """
    Controller for VSIC 2025 Excel to JSON conversion.

    Exit codes:
        0: Success
        1: Configuration error (file not found, invalid format)
        2: IO error
    """

    def __init__(
        self,
        excel_repository: Vsic2025ExcelRepository,
        parser_service: Vsic2025ParserService,
        json_repository: Vsic2025JsonRepository,
    ):
        self.excel_repository = excel_repository
        self.parser_service = parser_service
        self.json_repository = json_repository

    def execute(
        self,
        input_path: Path,
        output_path: Path,
    ) -> int:
        """
        Execute the VSIC 2025 conversion.

        Args:
            input_path: Path to input Excel file (vsic-2025.xlsx).
            output_path: Path to output JSON file.

        Returns:
            Exit code (0=success, 1=config error, 2=IO error).
        """
        try:
            logger.info(f"Reading VSIC 2025 Excel file: {input_path}")
            rows = self.excel_repository.read_rows(input_path)
            logger.info(f"Found {len(rows)} data rows")

            logger.info("Parsing VSIC 2025 entries with nested children")
            entries: List[Vsic2025Entry] = self.parser_service.parse_rows(rows)
            logger.info(f"Parsed {len(entries)} level 4 entries")

            logger.info(f"Writing nested JSON to: {output_path}")
            self.json_repository.write_entries(
                entries=entries,
                output_path=output_path,
                source=str(input_path),
            )

            logger.info("VSIC 2025 conversion complete")
            return 0

        except FileNotFoundError as e:
            logger.error(f"Input file not found: {e}")
            return 1

        except ValueError as e:
            logger.error(f"Invalid file format: {e}")
            return 1

        except OSError as e:
            logger.error(f"IO error: {e}")
            return 2

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return 1
