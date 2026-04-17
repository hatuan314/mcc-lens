"""
Tests cho Models module.
"""

import pytest
from app.models.base import BaseModel


class TestModel(BaseModel):
    """Test model implementation."""

    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict) -> "TestModel":
        """Create from dictionary."""
        return cls(name=data["name"], value=data["value"])


def test_base_model_to_dict():
    """Test to_dict method."""
    model = TestModel(name="test", value=42)
    result = model.to_dict()
    assert result == {"name": "test", "value": 42}


def test_base_model_from_dict():
    """Test from_dict method."""
    data = {"name": "test", "value": 42}
    model = TestModel.from_dict(data)
    assert model.name == "test"
    assert model.value == 42
