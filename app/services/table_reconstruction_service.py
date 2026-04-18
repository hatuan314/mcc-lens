"""
Table Reconstruction Service implementation.
"""

from typing import Dict, List, Tuple

from loguru import logger

from app.models.mcc_entry import BBoxTextItem


class TableReconstructionService:
    """
    Service for reconstructing table structure from OCR regions.

    Attributes:
        y_threshold_pct: Threshold for row grouping as percentage of image height.
    """

    def __init__(self, y_threshold_pct: float = 0.01):
        """
        Initialize TableReconstructionService.

        Args:
            y_threshold_pct: Y-axis threshold for row grouping (default 0.01 = 1% of height).
        """
        self.y_threshold_pct = y_threshold_pct

    def reconstruct(
        self, regions: List[BBoxTextItem], image_size: Tuple[int, int]
    ) -> List[Dict[str, str]]:
        """
        Reconstruct table rows from OCR regions.

        Args:
            regions: List of text regions with bounding boxes.
            image_size: Tuple of (width, height) of the original image.

        Returns:
            List of row dictionaries with keys: mcc, title_description, included, similar_merchants.
        """
        if not regions:
            logger.warning("No regions provided for table reconstruction")
            return []

        # Step 1: Group regions by rows
        rows = self._group_by_rows(regions, image_size[1])

        # Step 2: Assign columns to each region
        column_assignments = self._assign_columns(regions, image_size[0])

        # Step 3: Build row dictionaries
        reconstructed_rows = self._build_rows(rows, column_assignments)

        # Step 4: Merge multi-line entries
        merged_rows = self._merge_multiline(reconstructed_rows)

        logger.debug(f"Reconstructed {len(merged_rows)} table rows")
        return merged_rows

    def _group_by_rows(
        self, regions: List[BBoxTextItem], image_height: int
    ) -> List[List[BBoxTextItem]]:
        """
        Group regions by Y-axis proximity.

        Args:
            regions: List of text regions.
            image_height: Height of the image for threshold calculation.

        Returns:
            List of row groups, each containing regions in the same row.
        """
        if not regions:
            return []

        # Sort regions by Y coordinate
        sorted_regions = sorted(regions, key=lambda r: r.bbox[0])

        y_threshold = image_height * self.y_threshold_pct
        rows = []
        current_row = [sorted_regions[0]]

        for region in sorted_regions[1:]:
            y_current = region.bbox[0]
            y_last = current_row[-1].bbox[0]

            # If Y distance is within threshold, same row
            if abs(y_current - y_last) <= y_threshold:
                current_row.append(region)
            else:
                # New row
                rows.append(current_row)
                current_row = [region]

        rows.append(current_row)

        # Sort regions within each row by X coordinate
        for row in rows:
            row.sort(key=lambda r: r.bbox[1])

        return rows

    def _assign_columns(
        self, regions: List[BBoxTextItem], image_width: int
    ) -> Dict[BBoxTextItem, str]:
        """
        Assign column names to regions based on X position.

        Uses dynamic column thresholds based on typical MCC table layout:
        - MCC: ~10% of width
        - Title/Description: ~50% of width
        - Included: ~75% of width
        - Similar: ~90% of width

        Args:
            regions: List of text regions.
            image_width: Width of the image.

        Returns:
            Dictionary mapping region to column name.
        """
        column_thresholds = {
            "mcc": 0.10,
            "title_description": 0.50,
            "included": 0.75,
            "similar_merchants": 0.90,
        }

        assignments = {}

        for region in regions:
            x_center = (region.bbox[1] + region.bbox[3]) / 2
            x_normalized = x_center / image_width

            # Find column based on X position
            if x_normalized < column_thresholds["mcc"]:
                assignments[region] = "mcc"
            elif x_normalized < column_thresholds["title_description"]:
                assignments[region] = "title_description"
            elif x_normalized < column_thresholds["included"]:
                assignments[region] = "included"
            else:
                assignments[region] = "similar_merchants"

        return assignments

    def _build_rows(
        self, row_groups: List[List[BBoxTextItem]], column_assignments: Dict[BBoxTextItem, str]
    ) -> List[Dict[str, str]]:
        """
        Build row dictionaries from grouped regions and column assignments.

        Args:
            row_groups: List of row groups.
            column_assignments: Mapping of region to column name.

        Returns:
            List of row dictionaries.
        """
        rows = []

        for group in row_groups:
            row_dict = {
                "mcc": "",
                "title_description": "",
                "included": "",
                "similar_merchants": "",
            }

            for region in group:
                column = column_assignments.get(region, "")
                if column in row_dict:
                    row_dict[column] += " " + region.text
                    row_dict[column] = row_dict[column].strip()

            rows.append(row_dict)

        return rows

    def _merge_multiline(self, rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Merge multi-line entries where subsequent rows have empty MCC column.

        Args:
            rows: List of row dictionaries.

        Returns:
            List of merged row dictionaries.
        """
        if not rows:
            return []

        merged = []
        current_row = rows[0].copy()

        for row in rows[1:]:
            # If current row has MCC and next row doesn't, merge
            if current_row["mcc"] and not row["mcc"]:
                # Merge non-empty fields
                for key in ["title_description", "included", "similar_merchants"]:
                    if row[key]:
                        if current_row[key]:
                            current_row[key] += "\n" + row[key]
                        else:
                            current_row[key] = row[key]
            else:
                # Save current row and start new one
                merged.append(current_row)
                current_row = row.copy()

        merged.append(current_row)
        return merged

    def visualize_results(
        self, image_path, rows: List[Dict[str, str]]
    ):
        """
        Visualize reconstructed table on image.

        Args:
            image_path: Path to the original image.
            rows: Reconstructed table rows.

        Returns:
            PIL Image with bounding boxes and labels drawn.
        """
        from PIL import Image, ImageDraw, ImageFont

        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        # Try to load a font, fallback to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except Exception:
                font = ImageFont.load_default()

        # Draw table structure visualization
        # This is a placeholder - actual implementation would need region coordinates
        # For now, just add a watermark indicating reconstruction was performed
        draw.text(
            (10, 10),
            f"Table Reconstruction: {len(rows)} rows",
            fill="red",
            font=font,
        )

        return image
