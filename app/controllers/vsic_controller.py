"""
VSIC Convert Controller.
"""

from pathlib import Path
from typing import List

from loguru import logger

from app.models.vsic_entry import VsicEntry
from app.services.protocols import VsicParser, VsicRepository, VsicWriter


class VsicController:
    """
    Controller for VSIC Excel to JSON conversion.

    Exit codes:
        0: Success
        1: Configuration error
        2: IO error
    """

    def __init__(
        self,
        excel_repository: VsicRepository,
        parser_service: VsicParser,
        json_repository: VsicWriter,
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
        Execute the conversion.

        Args:
            input_path: Path to input Excel file.
            output_path: Path to output JSON file.

        Returns:
            Exit code (0=success, 1=config error, 2=IO error).
        """
        try:
            logger.info(f"Reading Excel file: {input_path}")
            rows = self.excel_repository.read_rows(input_path)
            logger.info(f"Found {len(rows)} rows")

            logger.info("Parsing VSIC entries")
            entries: List[VsicEntry] = self.parser_service.parse_rows(rows)
            logger.info(f"Parsed {len(entries)} entries")

            logger.info(f"Writing JSON to: {output_path}")
            self.json_repository.write_entries(entries, output_path)

            logger.info("Conversion complete")
            return 0

        except FileNotFoundError as e:
            logger.error(f"Input file not found: {e}")
            return 1

        except OSError as e:
            logger.error(f"IO error: {e}")
            return 2

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return 1
