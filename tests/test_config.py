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


def test_config_wokushop_validation():
    """Test WokuShop provider configuration validation."""
    # Lưu giá trị gốc
    original_provider = getattr(Config, "LLM_PROVIDER", "ollama")
    original_api_key = getattr(Config, "WOKUSHOP_API_KEY", None)

    try:
        # Nếu LLM_PROVIDER là wokushop và WOKUSHOP_API_KEY không được set -> báo lỗi
        Config.LLM_PROVIDER = "wokushop"
        Config.WOKUSHOP_API_KEY = None
        with pytest.raises(ValueError) as excinfo:
            Config.validate()
        assert "WOKUSHOP_API_KEY" in str(excinfo.value)

        # Nếu có API key -> validate thành công
        Config.WOKUSHOP_API_KEY = "dummy-api-key"
        Config.validate()
    finally:
        # Restore giá trị gốc
        if hasattr(Config, "LLM_PROVIDER"):
            Config.LLM_PROVIDER = original_provider
        if hasattr(Config, "WOKUSHOP_API_KEY"):
            Config.WOKUSHOP_API_KEY = original_api_key
