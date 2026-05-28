"""
VSIC 2025 Entry domain models with nested children_level5 structure.
"""

from typing import List

from pydantic import BaseModel as PydanticBaseModel, Field


class VsicLevel5Child(PydanticBaseModel):
    """
    Child entry for VSIC level 5 (detailed classification).

    Attributes:
        code: VSIC level 5 code string (e.g., "01110", "01119").
        title: Title of the VSIC level 5 category.
    """

    code: str = Field(..., description="VSIC level 5 code as string")
    title: str = Field(default="", description="Category title")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "01110",
                "title": "Trồng lúa hạt",
            }
        },
    }


class Vsic2025Entry(PydanticBaseModel):
    """
    Domain model for VSIC 2025 entry (level 4 with nested level 5 children).

    Attributes:
        code: VSIC level 4 code string (e.g., "0111", "0112").
        title: Title of the VSIC level 4 category.
        children_level5: List of level 5 child entries.
    """

    code: str = Field(..., description="VSIC level 4 code as string")
    title: str = Field(default="", description="Category title")
    children_level5: List[VsicLevel5Child] = Field(
        default_factory=list,
        description="List of level 5 child entries"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "0111",
                "title": "Trồng lúa",
                "children_level5": [
                    {"code": "01110", "title": "Trồng lúa hạt"},
                    {"code": "01119", "title": "Trồng lúa khác"},
                ],
            }
        },
    }


class Vsic2025Output(PydanticBaseModel):
    """
    Wrapper model for VSIC 2025 JSON output.

    Attributes:
        source: Input file path used for conversion.
        total_vsic_count: Number of level 4 entries in vsic_list.
        vsic_list: List of VSIC 2025 entries (level 4 with children).
    """

    source: str = Field(..., description="Input Excel file path")
    total_vsic_count: int = Field(..., description="Number of level 4 entries")
    vsic_list: List[Vsic2025Entry] = Field(..., description="List of VSIC entries")

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "assets/vsic-vn/vsic-2025.xlsx",
                "total_vsic_count": 497,
                "vsic_list": [
                    {
                        "code": "0111",
                        "title": "Trồng lúa",
                        "children_level5": [
                            {"code": "01110", "title": "Trồng lúa hạt"},
                        ],
                    }
                ],
            }
        },
    }
