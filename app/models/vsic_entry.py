"""
VSIC Entry domain model.
"""

from pydantic import BaseModel as PydanticBaseModel, Field


class VsicEntry(PydanticBaseModel):
    """
    Domain model for VSIC (Vietnam Standard Industrial Classification) entry.

    Attributes:
        code: VSIC code string (e.g., "1110", "01100") — always string.
        title: Title of the VSIC category.
        digits: Number of digits in code (4 or 5).
    """

    code: str = Field(..., description="VSIC code as string")
    title: str = Field(default="", description="Category title")
    digits: int = Field(..., description="Number of digits (4 or 5)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "1110",
                "title": "Trồng lúa",
                "digits": 4,
            }
        },
    }
