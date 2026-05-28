"""
VSIC 2025 JSON Repository implementation.
"""

import json
from pathlib import Path
from typing import List

from loguru import logger

from app.models.vsic_2025_entry import Vsic2025Entry, Vsic2025Output


class Vsic2025JsonRepository:
    """
    Repository for saving VSIC 2025 entries to JSON file with nested schema.
    """

    def write_entries(
        self,
        entries: List[Vsic2025Entry],
        output_path: Path,
        source: str,
    ) -> None:
        """
        Write VSIC 2025 entries to JSON file with nested wrapper schema.

        Args:
            entries: List of Vsic2025Entry objects to save.
            output_path: Path to output JSON file.
            source: Input file path to include in output metadata.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output = Vsic2025Output(
            source=source,
            total_vsic_count=len(entries),
            vsic_list=entries,
        )

        data = output.model_dump(mode="json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Wrote {len(entries)} level 4 entries to {output_path} "
            f"(total level 5 children: "
            f"{sum(len(e.children_level5) for e in entries)})"
        )
