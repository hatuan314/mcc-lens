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

    vsic_2025_parser = subparsers.add_parser(
        "convert-vsic-2025",
        help="Convert VSIC 2025 Excel to JSON with nested children_level5",
    )
    vsic_2025_parser.add_argument(
        "--input",
        "-i",
        dest="vsic_2025_input",
        type=Path,
        default=Path("assets/vsic-vn/vsic-2025.xlsx"),
        help="Input Excel file path (default: assets/vsic-vn/vsic-2025.xlsx)",
    )
    vsic_2025_parser.add_argument(
        "--output",
        "-o",
        dest="vsic_2025_output",
        type=Path,
        default=Path("output/vsic-vn.json"),
        help="Output JSON file path (default: output/vsic-vn.json)",
    )

    mapping_parser = subparsers.add_parser(
        "map-vsic-mcc",
        help="Map VSIC codes to MCC codes using Ollama LLM",
    )
    mapping_parser.add_argument(
        "--vsic-input",
        type=Path,
        default=Path("output/vsic-vn.json"),
        help="VSIC JSON input file (default: output/vsic-vn.json)",
    )
    mapping_parser.add_argument(
        "--mcc-input",
        type=Path,
        default=Path("output/mcc-visa.json"),
        help="MCC JSON input file (default: output/mcc-visa.json)",
    )
    mapping_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output/vsic-mcc-mapping.xlsx"),
        help="Simple Excel output file (default: output/vsic-mcc-mapping.xlsx)",
    )
    mapping_parser.add_argument(
        "--output-detail",
        type=Path,
        default=Path("output/vsic-mcc-mapping-detail.xlsx"),
        help="Detailed Excel output file (default: output/vsic-mcc-mapping-detail.xlsx)",
    )
    mapping_parser.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="Number of top-K MCC candidates for LLM (default: 15)",
    )
    mapping_parser.add_argument(
        "--ollama-host",
        type=str,
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )
    mapping_parser.add_argument(
        "--llm-model",
        type=str,
        default="qwen2.5:14b",
        help="LLM model name (default: qwen2.5:14b)",
    )
    mapping_parser.add_argument(
        "--embedding-model",
        type=str,
        default="bge-m3",
        help="Embedding model name (default: bge-m3)",
    )
    mapping_parser.add_argument(
        "--template",
        type=Path,
        default=Path("assets/template/vsic_mcc_mapping_template.xlsx"),
        help="Excel template for detailed output (default: assets/template/vsic_mcc_mapping_template.xlsx)",
    )
    mapping_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint, skipping already-processed VSIC entries",
    )
    mapping_parser.add_argument(
        "--limit", type=int, help="Limit number of VSIC entries to process"
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

        if args.command == "convert-vsic-2025":
            logger.info("Starting VSIC 2025 Excel conversion...")
            logger.info(f"Input: {args.vsic_2025_input}")
            logger.info(f"Output: {args.vsic_2025_output}")

            from app.repositories.vsic_2025_excel_repository import (
                Vsic2025ExcelRepository,
            )
            from app.repositories.vsic_2025_json_repository import (
                Vsic2025JsonRepository,
            )
            from app.services.vsic_2025_parser_service import (
                Vsic2025ParserService,
            )
            from app.controllers.vsic_2025_controller import Vsic2025Controller

            excel_repo = Vsic2025ExcelRepository()
            parser = Vsic2025ParserService()
            json_repo = Vsic2025JsonRepository()

            controller = Vsic2025Controller(
                excel_repository=excel_repo,
                parser_service=parser,
                json_repository=json_repo,
            )
            return controller.execute(
                input_path=args.vsic_2025_input,
                output_path=args.vsic_2025_output,
            )

        if args.command == "map-vsic-mcc":
            logger.info("Starting VSIC to MCC mapping...")
            logger.info(f"VSIC input: {args.vsic_input}")
            logger.info(f"MCC input: {args.mcc_input}")
            logger.info(f"Output: {args.output}")
            logger.info(f"Output detail: {args.output_detail}")
            logger.info(f"Top-K: {args.top_k}")
            logger.info(f"Ollama host: {args.ollama_host}")
            logger.info(f"LLM model: {args.llm_model}")
            logger.info(f"Embedding model: {args.embedding_model}")
            logger.info(f"Resume: {args.resume}")
            if args.limit:
                logger.info(f"Limit: {args.limit}")

            from app.controllers.mapping_controller import MappingController

            controller = MappingController(
                ollama_host=args.ollama_host,
                llm_model=args.llm_model,
                embedding_model=args.embedding_model,
                template_path=args.template,
            )
            return controller.execute(
                vsic_input=args.vsic_input,
                mcc_input=args.mcc_input,
                output=args.output,
                output_detail=args.output_detail,
                top_k=args.top_k,
                resume=args.resume,
                limit=args.limit,
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
