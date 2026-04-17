"""
Tests cho Config module.
"""

import pytest
from app.config import Config


def test_config_environment():
    """Test environment configuration."""
    assert Config.ENVIRONMENT in ["development", "staging", "production"]


def test_config_debug_mode():
    """Test debug mode configuration."""
    assert isinstance(Config.DEBUG, bool)


def test_config_base_dir():
    """Test base directory configuration."""
    assert Config.BASE_DIR.exists()
