"""
MCC Convert Controller.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.convert_mcc_images_use_case import ConvertMCCImagesUseCase
from app.services.florence2_vision_service import Florence2VisionService
from app.services.table_reconstruction_service import TableReconstructionService
from app.services.mcc_parser_service import MCCParserService
from app.repositories.mcc_image_repository import MCCImageRepository
from app.repositories.mcc_json_repository import MCCJsonRepository
from app.views.progress_bar_view import ProgressBarView


class MCCConvertController:
    """
    Controller for MCC image to JSON conversion.

    Exit codes:
        0: Success (even if some images had errors)
        1: Configuration error
        2: Infrastructure error (model load failed)
        3: IO error (output write failed)
    """

    def __init__(self):
        self.use_case = ConvertMCCImagesUseCase(
            vision_service=Florence2VisionService(),
            table_reconstructor=TableReconstructionService(),
            parser_service=MCCParserService(),
            image_repository=MCCImageRepository(),
            json_repository=MCCJsonRepository(),
        )

    def execute(
        self,
        input_dir: Path,
        output_path: Path,
        device: Optional[str] = None,
        y_threshold_pct: float = 0.01,
        resume: bool = False,
    ) -> int:
        """
        Execute the conversion.

        Args:
            input_dir: Directory containing input images.
            output_path: Path to output JSON file.
            device: Device to run inference on (cuda/mps/cpu).
            y_threshold_pct: Y-axis threshold for row grouping.
            resume: Resume from checkpoint when True.

        Returns:
            Exit code (0=success, 1=config error, 2=infrastructure error, 3=IO error).
        """
        try:
            result = self.use_case.execute(
                input_dir=input_dir,
                output_path=output_path,
                device=device,
                y_threshold_pct=y_threshold_pct,
                resume=resume,
            )

            logger.info(f"Conversion complete: {result['total_entries']} entries")
            logger.info(f"Processed: {result['processed']}/{result['total_images']} images")

            if result["errors"]:
                logger.warning(f"Errors encountered: {len(result['errors'])}")
                for error in result["errors"]:
                    logger.warning(f"  - {error['file']}: {error['error']}")

            return 0

        except FileNotFoundError as e:
            logger.error(f"Input directory not found: {e}")
            return 1

        except Exception as e:
            # Check if it's a model load error (infrastructure)
            error_msg = str(e).lower()
            if "model" in error_msg or "florence" in error_msg or "torch" in error_msg:
                logger.error(f"Infrastructure error (model load failed): {e}")
                return 2

            # Check if it's an IO error
            if "io" in error_msg or "permission" in error_msg or "disk" in error_msg:
                logger.error(f"IO error: {e}")
                return 3

            # Default to config error
            logger.error(f"Conversion failed: {e}")
            return 1
