"""
Florence-2 Vision Service implementation.
"""

import json
from pathlib import Path
from typing import List, Optional

from loguru import logger

from app.models.mcc_entry import BBoxTextItem


class Florence2VisionService:
    """
    Vision service using Florence-2 model for OCR with region detection.

    Attributes:
        model_name: HuggingFace model name.
        device: Device to run inference on (cuda/mps/cpu).
        cache_dir: Directory to cache OCR results per image (avoids re-running OCR).
    """

    def __init__(
        self,
        model_name: str = "microsoft/Florence-2-large",
        device: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        self.model_name = model_name
        self._device = device
        self._model = None
        self._processor = None
        self.cache_dir = cache_dir or Path("out/.ocr_cache")

    @property
    def device(self) -> str:
        """Auto-select device if not explicitly set."""
        if self._device is not None:
            return self._device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def _load_model(self) -> None:
        """Lazy load model and processor on first use."""
        if self._model is not None:
            return

        logger.info(f"Loading Florence-2 model: {self.model_name}")
        logger.info(f"Using device: {self.device}")

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor

            self._processor = AutoProcessor.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float32,
            )
            self._model.to(self.device)
            self._model.eval()
            logger.info("Florence-2 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Florence-2 model: {e}")
            raise

    def _cache_path(self, image_path: Path) -> Path:
        """Return path to cached OCR result for a given image."""
        return self.cache_dir / f"{image_path.stem}.json"

    def _load_from_cache(self, image_path: Path) -> Optional[List[BBoxTextItem]]:
        """Load OCR regions from cache if available and newer than image."""
        cache_file = self._cache_path(image_path)
        if not cache_file.exists():
            return None
        try:
            if cache_file.stat().st_mtime < image_path.stat().st_mtime:
                logger.debug(f"Cache stale for {image_path.name}")
                return None
            with cache_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            regions = [
                BBoxTextItem(text=r["text"], bbox=tuple(r["bbox"]))
                for r in data.get("regions", [])
            ]
            logger.info(f"Loaded {len(regions)} regions from cache: {image_path.name}")
            return regions
        except Exception as e:
            logger.warning(f"Failed to load OCR cache for {image_path.name}: {e}")
            return None

    def _save_to_cache(self, image_path: Path, regions: List[BBoxTextItem]) -> None:
        """Persist OCR regions to cache."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self._cache_path(image_path)
            data = {
                "image": image_path.name,
                "regions": [{"text": r.text, "bbox": list(r.bbox)} for r in regions],
            }
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved OCR cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save OCR cache for {image_path.name}: {e}")

    def extract_regions(self, image_path: Path) -> List[BBoxTextItem]:
        """
        Extract text regions with bounding boxes from an image.

        Uses disk cache keyed by image stem. Cache is invalidated when the
        image file is newer than the cache.

        Args:
            image_path: Path to the image file.

        Returns:
            List of BBoxTextItem with text and normalized bbox coordinates (y1, x1, y2, x2).
        """
        cached = self._load_from_cache(image_path)
        if cached is not None:
            return cached

        self._load_model()

        try:
            import torch
            from PIL import Image

            image = Image.open(image_path).convert("RGB")
            image_size = (image.width, image.height)

            # Use OCR_WITH_REGION task for bounding box detection
            task_prompt = "<OCR_WITH_REGION>"
            inputs = self._processor(
                text=task_prompt,
                images=image,
                return_tensors="pt",
            )

            if inputs is None:
                raise ValueError("Processor returned None inputs")

            # Move inputs to device
            inputs = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=3072,
                    num_beams=3,
                    do_sample=False,
                )

            generated_text = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=False,
            )[0]

            parsed_answer = self._processor.post_process_generation(
                generated_text,
                task=task_prompt,
                image_size=image_size,
            )

            if parsed_answer is None:
                logger.warning(f"post_process_generation returned None for {image_path.name}")
                return []

            ocr_result = parsed_answer.get(task_prompt, {})
            logger.debug(f"Florence-2 raw output keys: {list(parsed_answer.keys())}")
            if isinstance(ocr_result, dict):
                logger.debug(f"OCR result keys: {list(ocr_result.keys())}, "
                             f"num_boxes={len(ocr_result.get('quad_boxes', []))}, "
                             f"num_labels={len(ocr_result.get('labels', []))}")
            else:
                logger.debug(f"OCR result type: {type(ocr_result)}, sample: {str(ocr_result)[:200]}")
            if not ocr_result:
                logger.warning(f"No regions found for {image_path.name}")
                return []

            bbox_items = self._parse_regions_to_bbox_items(ocr_result, image_size)

            logger.debug(
                f"Extracted {len(bbox_items)} regions from {image_path.name}"
            )
            self._save_to_cache(image_path, bbox_items)
            return bbox_items

        except Exception as e:
            logger.error(f"Failed to extract regions from {image_path}: {e}")
            raise

    def _parse_regions_to_bbox_items(
        self, ocr_result: dict, image_size: tuple
    ) -> List[BBoxTextItem]:
        """
        Parse Florence-2 OCR_WITH_REGION output to BBoxTextItem.

        Florence-2 returns:
            {"quad_boxes": [[x1,y1,x2,y2,x3,y3,x4,y4], ...], "labels": ["text1", ...]}
        where each quad_box has 8 coordinates (4 corners in pixels).

        Args:
            ocr_result: Dict with "quad_boxes" and "labels" keys.
            image_size: Tuple of (width, height) for normalization.

        Returns:
            List of BBoxTextItem with normalized bbox (y1, x1, y2, x2).
        """
        bbox_items: List[BBoxTextItem] = []
        width, height = image_size

        quad_boxes = ocr_result.get("quad_boxes", []) or []
        labels = ocr_result.get("labels", []) or []

        for quad, label in zip(quad_boxes, labels):
            if not label or not quad or len(quad) < 8:
                continue
            # quad = [x1,y1,x2,y2,x3,y3,x4,y4] — 4 corners
            xs = [quad[0], quad[2], quad[4], quad[6]]
            ys = [quad[1], quad[3], quad[5], quad[7]]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            normalized_bbox = (
                y_min / height,
                x_min / width,
                y_max / height,
                x_max / width,
            )
            # Strip label (Florence-2 may prepend special tokens)
            text = str(label)
            for tok in ("</s>", "<s>", "<pad>"):
                text = text.replace(tok, "")
            text = text.strip()
            if text:
                bbox_items.append(BBoxTextItem(text=text, bbox=normalized_bbox))

        return bbox_items

