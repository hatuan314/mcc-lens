"""
MCC Entry domain model.
"""

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel as PydanticBaseModel, Field, model_validator


@dataclass(frozen=True)
class SimilarMerchant:
    """
    Dataclass representing a similar merchant entry.

    Attributes:
        mcc: 4-digit MCC code of the similar merchant.
        title: Name/description of the similar merchant.
    """

    mcc: str
    title: str


class MCCEntry(PydanticBaseModel):
    """
    Domain model for MCC (Merchant Category Code) entry.

    Attributes:
        mcc: 4-digit MCC code, or empty string when unparsed.
        title: Short title of the MCC category.
        description: Detailed description of the MCC category.
        included_in_mcc: List of items included in this MCC category.
        similar_merchants: List of similar merchants (with their MCC codes).
        source_image: Source image filename (required for provenance).
        unparsed: True when the entry could not be parsed into structured data.
    """

    mcc: str = Field(default="")
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    included_in_mcc: List[str] = Field(default_factory=list)
    similar_merchants: List[SimilarMerchant] = Field(default_factory=list)
    source_image: str
    unparsed: bool = Field(default=False, alias="_unparsed")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "mcc": "5812",
                "title": "Eating Places and Restaurants",
                "description": "Establishments which serve food and beverages...",
                "included_in_mcc": ["Restaurants", "Cafes", "Food Courts"],
                "similar_merchants": [
                    {"mcc": "5814", "title": "Fast Food Restaurants"},
                ],
                "source_image": "mcc-visa-01.jpg",
                "_unparsed": False,
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
