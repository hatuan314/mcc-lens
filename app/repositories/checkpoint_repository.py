"""
Checkpoint Repository implementation.

Stores the set of already-processed image filenames to support `--resume`.
"""

import json
import unicodedata
from pathlib import Path
from typing import Set

from loguru import logger


def _nfc(value: str) -> str:
    """Normalize a filename to NFC so macOS NFD filesystem names match JSON content."""
    return unicodedata.normalize("NFC", value)


class CheckpointRepository:
    """
    File-backed checkpoint repository.

    All filenames are stored and compared in NFC form to avoid mismatches
    between macOS filesystem (NFD) and Python string literals (NFC).

    Attributes:
        checkpoint_path: Path to the JSON checkpoint file.
    """

    def __init__(self, checkpoint_path: Path):
        self.checkpoint_path = checkpoint_path
        self._done: Set[str] = set()

    def load(self) -> Set[str]:
        """Load the set of already-processed filenames from disk (NFC-normalized)."""
        if not self.checkpoint_path.exists():
            return set()
        try:
            data = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._done = {_nfc(name) for name in data if isinstance(name, str)}
            else:
                self._done = set()
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load checkpoint {self.checkpoint_path}: {e}")
            self._done = set()
        return set(self._done)

    def mark_done(self, filename: str) -> None:
        """Append a filename to the checkpoint (NFC-normalized) and persist immediately."""
        self._done.add(_nfc(filename))
        self._persist()

    def clear(self) -> None:
        """Delete the checkpoint file after a successful run."""
        self._done.clear()
        try:
            if self.checkpoint_path.exists():
                self.checkpoint_path.unlink()
        except OSError as e:
            logger.warning(f"Failed to clear checkpoint {self.checkpoint_path}: {e}")

    def _persist(self) -> None:
        try:
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            self.checkpoint_path.write_text(
                json.dumps(sorted(self._done), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning(f"Failed to persist checkpoint {self.checkpoint_path}: {e}")
