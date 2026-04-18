"""
MCC JSON Repository implementation.
"""

import json
from pathlib import Path
from typing import List

from app.models.mcc_entry import MCCEntry


class MCCJsonRepository:
    """
    Repository for saving MCC entries to JSON file.
    """

    def save(self, entries: List[MCCEntry], output_path: Path) -> None:
        """
        Save MCC entries to JSON file.

        Args:
            entries: List of MCCEntry objects to save.
            output_path: Path to output JSON file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [entry.model_dump(mode="json", by_alias=True) for entry in entries]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
