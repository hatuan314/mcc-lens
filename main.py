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
        help="Convert MCC images to JSON using Surya OCR",
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
        "--resume",
        action="store_true",
        help="Resume from checkpoint, skipping already-processed images",
    )

    vsic_parser = subparsers.add_parser(
        "convert-vsic",
        help="Convert VSIC Excel to JSON",
    )
    vsic_parser.add_argument(
        "--input",
        "-i",
        dest="input_path",
        type=Path,
        default=Path("assets/vsic-vn/vsic.xlsx"),
        help="Input Excel file path (default: assets/vsic-vn/vsic.xlsx)",
    )
    vsic_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output/vsic.json"),
        help="Output JSON file path (default: output/vsic.json)",
    )

    args = parser.parse_args()

    try:
        setup_logging()

        if args.command == "convert-mcc":
            logger.info("Starting MCC image conversion...")
            logger.info(f"Input: {args.input_dir}")
            logger.info(f"Output: {args.output}")

            from app.services.surya_ocr_service import SuryaOCRService
            from app.services.mcc_table_parser_service import MCCTableParserService
            from app.repositories.mcc_image_repository import MCCImageRepository
            from app.repositories.mcc_json_repository import MCCJsonRepository
            from app.repositories.checkpoint_repository import CheckpointRepository

            ocr_service = SuryaOCRService()
            table_parser = MCCTableParserService()
            image_repo = MCCImageRepository()
            json_repo = MCCJsonRepository()
            checkpoint_repo = CheckpointRepository(
                checkpoint_path=args.output.parent / ".mcc-convert-progress.json"
            )

            controller = MCCConvertController(
                ocr_service=ocr_service,
                table_parser=table_parser,
                image_repository=image_repo,
                json_repository=json_repo,
                checkpoint_repository=checkpoint_repo,
            )
            return controller.execute(
                input_dir=args.input_dir,
                output_path=args.output,
                resume=args.resume,
            )

        if args.command == "convert-vsic":
            logger.info("Starting VSIC Excel conversion...")
            logger.info(f"Input: {args.input_path}")
            logger.info(f"Output: {args.output}")

            from app.repositories.vsic_excel_repository import VsicExcelRepository
            from app.repositories.vsic_json_repository import VsicJsonRepository
            from app.services.vsic_parser_service import VsicParserService
            from app.controllers.vsic_controller import VsicController

            excel_repo = VsicExcelRepository()
            parser = VsicParserService()
            json_repo = VsicJsonRepository()

            controller = VsicController(
                excel_repository=excel_repo,
                parser_service=parser,
                json_repository=json_repo,
            )
            return controller.execute(
                input_path=args.input_path,
                output_path=args.output,
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
