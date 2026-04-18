"""
Quick test: load Florence-2 model and OCR 1 image to verify fix.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.services.florence2_vision_service import Florence2VisionService


def main() -> int:
    image_dir = Path("assets/mcc-visa")
    images = sorted(image_dir.glob("*.jpg"))
    if not images:
        logger.error(f"No images found in {image_dir}")
        return 1

    test_image = images[0]
    logger.info(f"Testing Florence-2 with image: {test_image.name}")

    service = Florence2VisionService(device="cpu")

    t0 = time.time()
    logger.info("Loading model (may take a while on first run)...")
    try:
        service._load_model()
        logger.success(f"Model loaded in {time.time() - t0:.1f}s")
    except Exception as e:
        logger.error(f"Model load FAILED: {e}")
        return 2

    t1 = time.time()
    logger.info("Running OCR...")
    try:
        regions = service.extract_regions(test_image)
        logger.success(
            f"OCR done in {time.time() - t1:.1f}s — {len(regions)} regions"
        )
        if regions:
            logger.info(f"First region: text={regions[0].text!r}, bbox={regions[0].bbox}")
        return 0
    except Exception as e:
        logger.error(f"OCR FAILED: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
