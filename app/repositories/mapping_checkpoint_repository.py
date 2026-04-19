"""Repository for managing VSIC-to-MCC mapping checkpoint state."""

import json
import os
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.protocols import MappingCheckpointRepository as MappingCheckpointRepo


class MappingCheckpointRepository(MappingCheckpointRepo):
    """JSON-based checkpoint repository for mapping progress."""

    def __init__(self, checkpoint_path: Path) -> None:
        """
        Initialize checkpoint repository.

        Args:
            checkpoint_path: Path to checkpoint JSON file.
        """
        self.checkpoint_path = checkpoint_path
        self._data: Optional[dict] = None

    def load(self) -> dict:  # type: ignore[return]
        """
        Load completed mapping results from checkpoint.

        Returns:
            Dict mapping VSIC codes to results. Empty if file not found.
        """
        if self._data is not None:
            return self._data

        if not self.checkpoint_path.exists():
            logger.debug(
                f"Checkpoint file not found at {self.checkpoint_path}, starting fresh"
            )
            self._data = {}
            return self._data

        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(
                    f"Loaded checkpoint with {len(data)} completed entries from "
                    f"{self.checkpoint_path}"
                )
                self._data = data
                return self._data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load checkpoint file: {e}. Starting fresh.")
            self._data = {}
            return self._data

    def save(self, vsic_code: str, result: dict) -> None:
        """
        Save a single VSIC mapping result atomically.

        Uses write-to-temp + os.replace pattern to ensure atomicity.
        Uses cached data to avoid O(N²) disk reads.

        Args:
            vsic_code: VSIC code that was processed.
            result: Mapping result dict with top_results.
        """
        # Ensure data is loaded (uses cache)
        data = self.load()

        # Update with new result
        data[vsic_code] = result

        # Write to temp file first
        temp_path = self.checkpoint_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic replace
            os.replace(temp_path, self.checkpoint_path)
            logger.debug(f"Saved checkpoint for VSIC {vsic_code}")

        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(
                f"Failed to save checkpoint for VSIC {vsic_code}: {e}"
            ) from e
