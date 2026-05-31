#!/usr/bin/env python3
"""Kiểm tra sự chênh lệch mã VSIC giữa vsic-vn.json và vsicvn-mcc-mapping-detail.json."""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent / "output"
VSIC_FILE = ROOT / "vsic-vn.json"
MAPPING_FILE = ROOT / "vsicvn-mcc-mapping-detail.json"
MISSING_FILE = ROOT / "vsic-vn-missing.json"


def load_vsic_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["vsic_list"]


def load_mapped_codes(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {m["vsic_code"] for m in data["mappings"]}


def main() -> None:
    vsic_items = load_vsic_items(VSIC_FILE)
    vsic_codes = {item["code"] for item in vsic_items}
    mapped_codes = load_mapped_codes(MAPPING_FILE)

    missing_codes = vsic_codes - mapped_codes
    in_mapped_not_vsic = sorted(mapped_codes - vsic_codes)

    missing_items = sorted(
        [item for item in vsic_items if item["code"] in missing_codes],
        key=lambda x: x["code"],
    )

    output = {
        "source": "output/vsic-vn.json",
        "total_vsic_count": len(missing_items),
        "vsic_list": missing_items,
    }
    MISSING_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Tổng mã trong vsic-vn.json       : {len(vsic_codes)}")
    print(f"Tổng mã trong mapping-detail.json : {len(mapped_codes)}")
    print()

    print(f"=== Có trong vsic-vn nhưng CHƯA được mapping ({len(missing_items)}) — đã lưu vào {MISSING_FILE.name} ===")
    for item in missing_items:
        print(f"  {item['code']}  {item['title']}")

    print()
    print(f"=== Có trong mapping nhưng KHÔNG có trong vsic-vn ({len(in_mapped_not_vsic)}) ===")
    for code in in_mapped_not_vsic:
        print(f"  {code}")


if __name__ == "__main__":
    main()
