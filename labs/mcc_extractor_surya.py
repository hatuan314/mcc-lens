#!/usr/bin/env python3
"""
MCC Extractor dùng Surya OCR — chạy local, miễn phí, tối ưu cho Apple M1
Pipeline: Surya layout detection → OCR từng vùng → parse cấu trúc bảng → JSON

Cài đặt:
    pip install surya-ocr pillow

Lần chạy đầu tiên Surya sẽ tự download model (~1-2GB). Các lần sau dùng cache.

Usage:
    python mcc_extractor_surya.py --images page1.jpg page2.jpg --output mcc_list.json
    python mcc_extractor_surya.py --images visa_mcc_*.jpg --output mcc_list.json
"""

import json
import argparse
import re
import sys
from pathlib import Path
from PIL import Image


# ─────────────────────────────────────────────────────────
# Surya imports — lazy để tránh lỗi nếu chưa cài
# ─────────────────────────────────────────────────────────
def import_surya():
    try:
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        return RecognitionPredictor, DetectionPredictor, FoundationPredictor
    except ImportError as e:
        print(f"❌ Không import được surya-ocr: {e}")
        print("   Chạy: pip install surya-ocr")
        sys.exit(1)


# ─────────────────────────────────────────────────────────
# Bước 1: OCR toàn trang lấy text + tọa độ từng dòng
# ─────────────────────────────────────────────────────────
def ocr_page(image: Image.Image, recognition_predictor, detection_predictor) -> list[dict]:
    """
    Trả về danh sách dòng text với bounding box:
    [{"text": "...", "bbox": [x1, y1, x2, y2], "confidence": 0.99}, ...]

    API mới (Surya >= 0.14): RecognitionPredictor tự động chạy detection
    khi được truyền det_predictor, trả về List[OCRResult].
    """
    predictions = recognition_predictor([image], det_predictor=detection_predictor)
    rec = predictions[0]

    lines = []
    for line in rec.text_lines:
        if not line.text or not line.text.strip():
            continue
        bbox = list(line.bbox)  # [x1, y1, x2, y2]
        lines.append({
            "text": line.text.strip(),
            "bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
            "confidence": float(line.confidence) if line.confidence is not None else 1.0,
        })

    # Sắp xếp theo y (từ trên xuống), sau đó x (trái sang phải)
    lines.sort(key=lambda l: (round(l["bbox"][1] / 15), l["bbox"][0]))
    return lines


# ─────────────────────────────────────────────────────────
# Bước 2: Phân tích layout — xác định cột của bảng
# ─────────────────────────────────────────────────────────
def detect_table_columns(lines: list[dict], image_width: int) -> dict[str, tuple[int, int]]:
    """
    Bảng MCC có 4 cột cố định. Dùng x-coordinate để phân loại
    (tỷ lệ đã hiệu chỉnh theo layout của Visa Merchant Data Standards Manual):
      col_mcc:       x1 < 12%   (cột MCC code, ~9% trên ảnh 2550px)
      col_desc:      12% – 46%  (cột title + description, ~14%)
      col_included:  46% – 64%  (cột "Included in this MCC", ~48%)
      col_similar:   64% – 100% (cột "Similar Merchants", ~66%)
    """
    w = image_width
    return {
        "mcc":      (0,            int(w * 0.12)),
        "desc":     (int(w * 0.12), int(w * 0.46)),
        "included": (int(w * 0.46), int(w * 0.64)),
        "similar":  (int(w * 0.64), w),
    }


def get_column(x1: int, columns: dict) -> str:
    """Xác định dòng text thuộc cột nào dựa trên x1."""
    for col_name, (x_min, x_max) in columns.items():
        if x_min <= x1 < x_max:
            return col_name
    return "unknown"


# ─────────────────────────────────────────────────────────
# Bước 3: Gom nhóm dòng theo từng entry MCC
# ─────────────────────────────────────────────────────────
def is_mcc_code(text: str) -> bool:
    """Kiểm tra xem text có phải là MCC code (4 chữ số) không."""
    return bool(re.fullmatch(r"\d{4}", text.strip()))


def group_lines_into_entries(lines: list[dict], columns: dict) -> list[dict]:
    """
    Gom các dòng text thành từng entry MCC.
    Mỗi entry bắt đầu khi gặp một MCC code 4 chữ số ở cột 'mcc'.
    """
    entries = []
    current: dict | None = None

    for line in lines:
        x1 = line["bbox"][0]
        col = get_column(x1, columns)
        text = line["text"].strip()

        if col == "mcc" and is_mcc_code(text):
            # Bắt đầu entry mới
            if current is not None:
                entries.append(current)
            current = {
                "mcc": text,
                "_desc_lines": [],
                "_included_lines": [],
                "_similar_lines": [],
            }
        elif current is not None:
            if col == "desc":
                current["_desc_lines"].append(text)
            elif col == "included":
                current["_included_lines"].append(text)
            elif col == "similar":
                current["_similar_lines"].append(text)

    if current is not None:
        entries.append(current)

    return entries


# ─────────────────────────────────────────────────────────
# Bước 4: Parse từng entry thành cấu trúc JSON sạch
# ─────────────────────────────────────────────────────────
def parse_similar_merchant(text: str) -> dict | None:
    """
    Parse dòng dạng "5995 – Pet Shops, Pet Foods and Supplies Store"
    thành {"mcc": "5995", "title": "Pet Shops, Pet Foods and Supplies Store"}
    Hỗ trợ cả dấu '–' (en dash) và '-' (hyphen)
    """
    # Thử match pattern: 4 chữ số + dấu gạch ngang + title
    m = re.match(r"^(\d{4})\s*[–\-]\s*(.+)$", text.strip())
    if m:
        return {"mcc": m.group(1), "title": m.group(2).strip()}
    return None


def parse_entry(raw: dict) -> dict:
    """Chuyển raw entry thành cấu trúc JSON chuẩn."""
    desc_lines = raw["_desc_lines"]
    included_lines = raw["_included_lines"]
    similar_lines = raw["_similar_lines"]

    # Dòng đầu tiên của _desc_lines thường là title
    title = desc_lines[0] if desc_lines else None
    description = " ".join(desc_lines[1:]).strip() if len(desc_lines) > 1 else None

    # Loại bỏ các dòng trống hoặc chỉ có dấu câu
    included = [l for l in included_lines if len(l) > 2]

    # Parse similar merchants — có thể gồm cả tiếp nối từ dòng trước
    similar = []
    pending = None
    for line in similar_lines:
        parsed = parse_similar_merchant(line)
        if parsed:
            if pending:
                similar.append(pending)
            pending = parsed
        elif pending:
            # Dòng tiếp nối của title trước (vd: "Supplies Store" sau khi bị cắt)
            pending["title"] = pending["title"] + " " + line.strip()
        # Nếu không parse được và không có pending → bỏ qua (header row, v.v.)
    if pending:
        similar.append(pending)

    return {
        "mcc": raw["mcc"],
        "title": title,
        "description": description if description else None,
        "included_in_mcc": included if included else [],
        "similar_merchants": similar,
    }


# ─────────────────────────────────────────────────────────
# Bước 5: Dedup và sort
# ─────────────────────────────────────────────────────────
def deduplicate(entries: list[dict]) -> list[dict]:
    seen = {}
    for e in entries:
        mcc = e.get("mcc")
        if not mcc:
            continue
        if mcc not in seen:
            seen[mcc] = e
        else:
            # Giữ entry đầy đủ hơn (description dài hơn)
            existing_len = len(seen[mcc].get("description") or "")
            new_len = len(e.get("description") or "")
            if new_len > existing_len:
                seen[mcc] = e
    return sorted(seen.values(), key=lambda x: x.get("mcc", "0"))


# ─────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────
def process_images(image_paths: list[str], output_path: str):
    RecognitionPredictor, DetectionPredictor, FoundationPredictor = import_surya()

    print("\n⏳ Đang load Surya models (lần đầu sẽ download ~1–2GB)...")
    foundation_predictor = FoundationPredictor()
    recognition_predictor = RecognitionPredictor(foundation_predictor)
    detection_predictor = DetectionPredictor()
    print("✅ Models loaded\n")

    all_entries = []
    failed = []

    for image_path in image_paths:
        p = Path(image_path)
        if not p.exists():
            print(f"  ⚠️  Không tìm thấy file: {image_path}")
            failed.append(image_path)
            continue

        print(f"  📷 Đang xử lý: {p.name}")
        try:
            image = Image.open(image_path).convert("RGB")
            w, _ = image.size

            # OCR
            lines = ocr_page(image, recognition_predictor, detection_predictor)
            print(f"     → OCR thu được {len(lines)} dòng text")

            # Layout analysis
            columns = detect_table_columns(lines, w)

            # Group + parse
            raw_entries = group_lines_into_entries(lines, columns)
            parsed = [parse_entry(e) for e in raw_entries]

            print(f"     → Tìm thấy {len(parsed)} MCC entries")
            all_entries.extend(parsed)

        except Exception as e:
            print(f"  ❌ Lỗi khi xử lý {image_path}: {e}")
            failed.append(image_path)

    # Dedup + sort
    unique = deduplicate(all_entries)
    print(f"\n📊 Tổng raw: {len(all_entries)} | Sau dedup: {len(unique)} MCC entries")

    output = {
        "source": "Visa Merchant Data Standards Manual",
        "total_mcc_count": len(unique),
        "mcc_list": unique,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu: {output_path}")

    if failed:
        print(f"\n⚠️  {len(failed)} file thất bại: {', '.join(failed)}")


def main():
    parser = argparse.ArgumentParser(
        description="Chuyển ảnh danh sách MCC của VISA thành JSON (Surya OCR, miễn phí, M1 native)"
    )
    parser.add_argument("--images", nargs="+", required=True, help="Danh sách file ảnh")
    parser.add_argument("--output", default="mcc_list.json", help="File JSON output")
    args = parser.parse_args()

    # Expand glob nếu shell chưa expand
    image_paths = []
    for pat in args.images:
        matches = sorted(Path(".").glob(pat))
        image_paths.extend(str(m) for m in matches) if matches else image_paths.append(pat)

    if not image_paths:
        print("❌ Không tìm thấy file ảnh nào!")
        sys.exit(1)

    process_images(image_paths, args.output)


if __name__ == "__main__":
    main()
