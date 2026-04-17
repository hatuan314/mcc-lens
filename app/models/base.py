"""
Base Model class cho tất cả các business entities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class BaseModel(ABC):
    """
    Base class cho tất cả các models trong ứng dụng.
    Sử dụng dataclass để giảm boilerplate code.
    """

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi model thành dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation của model.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """
        Tạo model instance từ dictionary.

        Args:
            data: Dictionary chứa dữ liệu model.

        Returns:
            BaseModel: Instance của model.
        """
        pass
