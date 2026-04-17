"""
Cấu hình ứng dụng.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables từ file .env
load_dotenv()


class Config:
    """
    Class chứa tất cả cấu hình của ứng dụng.
    """

    # Base directory
    BASE_DIR: Path = Path(__file__).parent.parent

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

    # Database (nếu cần)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # API Keys (nếu cần)
    API_KEY: Optional[str] = os.getenv("API_KEY")

    @classmethod
    def validate(cls) -> None:
        """
        Validate các cấu hình bắt buộc.
        """
        if cls.ENVIRONMENT not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid ENVIRONMENT: {cls.ENVIRONMENT}")


# Validate config khi import
Config.validate()
