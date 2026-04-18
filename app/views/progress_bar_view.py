"""
Progress Bar View using tqdm.
"""

from typing import Iterable, Optional

from tqdm import tqdm


class ProgressBarView:
    """
    Wrapper around tqdm for displaying progress bars.
    """

    def __init__(
        self,
        total: Optional[int] = None,
        desc: str = "Processing",
        unit: str = "item",
    ):
        self.total = total
        self.desc = desc
        self.unit = unit
        self._bar: Optional[tqdm] = None

    def __enter__(self) -> "ProgressBarView":
        self._bar = tqdm(
            total=self.total,
            desc=self.desc,
            unit=self.unit,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._bar:
            self._bar.close()

    def update(self, n: int = 1) -> None:
        if self._bar:
            self._bar.update(n)

    def set_description(self, desc: str) -> None:
        if self._bar:
            self._bar.set_description(desc)

    def set_postfix(self, **kwargs) -> None:
        if self._bar:
            self._bar.set_postfix(**kwargs)

    @staticmethod
    def iterate(
        iterable: Iterable,
        desc: str = "Processing",
        unit: str = "item",
    ) -> Iterable:
        return tqdm(iterable, desc=desc, unit=unit)
