"""
MCC Convert Controller.
"""

from pathlib import Path

from loguru import logger

from app.services.convert_mcc_images_use_case import ConvertMCCImagesUseCase
from app.services.protocols import (
    CheckpointRepository,
    ImageRepository,
    JsonRepository,
    OCRService,
    TableParser,
)


class MCCConvertController:
    """
    Controller for MCC image to JSON conversion.

    Exit codes:
        0: Success (even if some images had errors)
        1: Configuration error
        2: Infrastructure error (model load failed)
        3: IO error (output write failed)
    """

    def __init__(
        self,
        ocr_service: OCRService,
        table_parser: TableParser,
        image_repository: ImageRepository,
        json_repository: JsonRepository,
        checkpoint_repository: CheckpointRepository,
    ):
        self.use_case = ConvertMCCImagesUseCase(
            ocr_service=ocr_service,
            table_parser=table_parser,
            image_repository=image_repository,
            json_repository=json_repository,
            checkpoint_repository=checkpoint_repository,
        )

    def execute(
        self,
        input_dir: Path,
        output_path: Path,
        resume: bool = False,
    ) -> int:
        """
        Execute the conversion.

        Args:
            input_dir: Directory containing input images.
            output_path: Path to output JSON file.
            resume: Resume from checkpoint when True.

        Returns:
            Exit code (0=success, 1=config error, 2=infrastructure error, 3=IO error).
        """
        try:
            result = self.use_case.execute(
                input_dir=input_dir,
                output_path=output_path,
                resume=resume,
            )

            logger.info(f"Conversion complete: {result['total_entries']} entries")
            logger.info(
                f"Processed: {result['processed']}/{result['total_images']} images"
            )

            if result["errors"]:
                logger.warning(f"Errors encountered: {len(result['errors'])}")
                for error in result["errors"]:
                    logger.warning(f"  - {error['file']}: {error['error']}")

            return 0

        except FileNotFoundError as e:
            logger.error(f"Input directory not found: {e}")
            return 1

        except Exception as e:
            error_msg = str(e).lower()
            if "model" in error_msg or "surya" in error_msg:
                logger.error(f"Infrastructure error (model load failed): {e}")
                return 2

            if "io" in error_msg or "permission" in error_msg or "disk" in error_msg:
                logger.error(f"IO error: {e}")
                return 3

            logger.error(f"Conversion failed: {e}")
            return 1
