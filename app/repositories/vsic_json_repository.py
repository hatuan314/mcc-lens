"""
VSIC JSON Repository implementation.
"""

import json
from pathlib import Path
from typing import List

from app.models.vsic_entry import VsicEntry


class VsicJsonRepository:
    """
    Repository for saving VSIC entries to JSON file.
    """

    def write_entries(self, entries: List[VsicEntry], output_path: Path) -> None:
        """
        Write VSIC entries to JSON file as a flat array.

        Args:
            entries: List of VsicEntry objects to save.
            output_path: Path to output JSON file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [entry.model_dump(mode="json") for entry in entries]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
