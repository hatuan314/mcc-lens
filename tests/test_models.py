"""
Tests cho Models module.
"""

import pytest
from app.models.mcc_entry import MCCEntry, SimilarMerchant
from app.models.ocr_line import OCRLine


def test_similar_merchant_creation():
    """Test SimilarMerchant dataclass."""
    merchant = SimilarMerchant(mcc="5814", title="Fast Food Restaurants")
    assert merchant.mcc == "5814"
    assert merchant.title == "Fast Food Restaurants"


def test_ocr_line_creation():
    """Test OCRLine dataclass."""
    line = OCRLine(text="5812", bbox=[10.0, 20.0, 50.0, 40.0], confidence=0.95)
    assert line.text == "5812"
    assert line.bbox == [10.0, 20.0, 50.0, 40.0]
    assert line.confidence == 0.95


def test_mcc_entry_valid():
    """Test MCCEntry with valid MCC code."""
    entry = MCCEntry(
        mcc="5812",
        title="Eating Places",
        description="Restaurants and cafes",
        included_in_mcc=["Restaurants"],
        similar_merchants=[SimilarMerchant(mcc="5814", title="Fast Food")],
        source_image="test.jpg",
    )
    assert entry.mcc == "5812"
    assert entry.title == "Eating Places"
    assert entry.unparsed is False


def test_mcc_entry_unparsed():
    """Test MCCEntry with unparsed=True bypasses validation."""
    entry = MCCEntry(
        mcc="invalid",
        source_image="test.jpg",
        unparsed=True,
    )
    assert entry.unparsed is True


def test_mcc_entry_invalid_mcc_raises():
    """Test MCCEntry with invalid MCC code raises ValueError."""
    with pytest.raises(ValueError, match="4-digit"):
        MCCEntry(mcc="abc", source_image="test.jpg")
