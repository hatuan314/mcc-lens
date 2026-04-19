"""Data Transfer Objects for VSIC to MCC mapping."""

from typing import List

from pydantic import BaseModel, Field


class RankedMcc(BaseModel):
    """Represents a ranked MCC candidate for a VSIC entry."""

    mcc_code: str = Field(..., description="4-character MCC code")
    mcc_title: str = Field(..., description="MCC title in English")
    score: float = Field(..., le=1.0, description="Cosine similarity from embedding")
    comment: str = Field(
        ..., description="Short explanation from LLM why this MCC fits"
    )


class MappingEntry(BaseModel):
    """Represents a complete mapping result for one VSIC entry."""

    vsic_code: str = Field(..., description="VSIC code")
    vsic_title: str = Field(..., description="VSIC title in Vietnamese")
    top_results: List[RankedMcc] = Field(
        default_factory=list,
        description="Top 1-3 ranked MCC candidates, empty list = NO_MATCH",
    )
