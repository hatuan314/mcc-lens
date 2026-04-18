"""
MCC Entry domain model.
"""

from dataclasses import dataclass
from typing import List

from pydantic import BaseModel, Field, model_validator


@dataclass(frozen=True)
class BBoxTextItem:
    """
    Dataclass representing a text region with bounding box.

    Attributes:
        text: Extracted text content.
        bbox: Bounding box as tuple (y1, x1, y2, x2) in normalized coordinates [0-1].
    """

    text: str
    bbox: tuple[float, float, float, float]


class MCCEntry(BaseModel):
    """
    Domain model for MCC (Merchant Category Code) entry.

    Attributes:
        mcc: 4-digit MCC code, or empty string when unparsed.
        title_description: Combined title and description of MCC.
        included: What is included in this MCC category.
        similar_merchants: List of similar merchants.
        source_image: Source image filename (required for provenance).
        unparsed: True when the page could not be parsed into structured entries.
    """

    mcc: str = Field(default="")
    title_description: str = Field(default="")
    included: str = Field(default="")
    similar_merchants: List[str] = Field(default_factory=list)
    source_image: str
    unparsed: bool = Field(default=False)

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "mcc": "5812",
                "title_description": "Eating Places and Restaurants",
                "included": "Establishments which serve food and beverages...",
                "similar_merchants": ["Restaurant", "Cafe", "Food Court"],
                "source_image": "mcc-visa-01.jpg",
                "unparsed": False,
            }
        },
    }

    @model_validator(mode="after")
    def validate_mcc(self) -> "MCCEntry":
        if self.unparsed:
            return self
        if self.mcc and not (self.mcc.isdigit() and len(self.mcc) == 4):
            raise ValueError("mcc must be a 4-digit string when unparsed=False")
        return self
