"""
Entry point của ứng dụng MCC Lens.
"""

import sys
from loguru import logger
from app.config import Config


def setup_logging() -> None:
    """
    Cấu hình logging cho ứng dụng.
    """
    logger.remove()  # Remove default handler

    # Console handler
    logger.add(
        sys.stderr,
        level=Config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # File handler (nếu cấu hình)
    if Config.LOG_FILE:
        logger.add(
            Config.LOG_FILE,
            level=Config.LOG_LEVEL,
            rotation="10 MB",
            retention="7 days",
        )


def main() -> int:
    """
    Main function của ứng dụng.

    Returns:
        int: Exit code (0 = success, 1 = error).
    """
    try:
        setup_logging()

        logger.info("Khởi động MCC Lens...")
        logger.info(f"Environment: {Config.ENVIRONMENT}")
        logger.info(f"Debug mode: {Config.DEBUG}")

        # TODO: Thêm logic chính của ứng dụng ở đây

        logger.info("MCC Lens đã khởi động thành công!")
        return 0

    except Exception as e:
        logger.error(f"Lỗi khởi động ứng dụng: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
