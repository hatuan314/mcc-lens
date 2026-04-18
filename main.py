"""
Entry point của ứng dụng MCC Lens.
"""

import sys
import argparse
from pathlib import Path

from loguru import logger
from app.config import Config
from app.controllers.mcc_convert_controller import MCCConvertController


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
    parser = argparse.ArgumentParser(
        description="MCC Lens - Convert MCC data between formats"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    convert_parser = subparsers.add_parser(
        "convert-mcc",
        help="Convert MCC images to JSON using Florence-2",
    )
    convert_parser.add_argument(
        "--input-dir",
        "--input",
        "-i",
        dest="input_dir",
        type=Path,
        default=Path("assets/mcc-visa"),
        help="Input directory containing MCC images (default: assets/mcc-visa)",
    )
    convert_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("out/mcc-visa.json"),
        help="Output JSON file path (default: out/mcc-visa.json)",
    )
    convert_parser.add_argument(
        "--device",
        "-d",
        choices=["auto", "cuda", "mps", "cpu"],
        default="auto",
        help="Device to run inference on (default: auto)",
    )
    convert_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint, skipping already-processed images",
    )
    convert_parser.add_argument(
        "--y-threshold",
        type=float,
        default=0.01,
        help="Y-axis threshold for row grouping as percentage of image height (default: 0.01)",
    )

    args = parser.parse_args()

    try:
        setup_logging()

        if args.command == "convert-mcc":
            logger.info("Starting MCC image conversion...")
            logger.info(f"Input: {args.input_dir}")
            logger.info(f"Output: {args.output}")
            logger.info(f"Y threshold: {args.y_threshold}")

            device = None if args.device == "auto" else args.device
            controller = MCCConvertController()
            return controller.execute(
                input_dir=args.input_dir,
                output_path=args.output,
                device=device,
                y_threshold_pct=args.y_threshold,
                resume=args.resume,
            )

        logger.info("Khởi động MCC Lens...")
        logger.info(f"Environment: {Config.ENVIRONMENT}")
        logger.info(f"Debug mode: {Config.DEBUG}")

        logger.info("MCC Lens đã khởi động thành công!")
        return 0

    except Exception as e:
        logger.error(f"Lỗi khởi động ứng dụng: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
