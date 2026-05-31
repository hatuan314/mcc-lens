#!/usr/bin/env python3
"""Script utility to split a large VSIC JSON file into multiple smaller JSON files.

This script parses the original VSIC JSON structure and slices its `vsic_list`
into smaller chunks (default: 20 elements per file), preserving metadata.
"""

import argparse
import json
import os
import math
from typing import Any, Dict, List


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments.

    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Split a large VSIC JSON file into smaller chunks."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="output/vsic-vn.json",
        help="Path to the original large JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="output/vsic_parts",
        help="Directory to save the split JSON files.",
    )
    parser.add_argument(
        "--chunk-size",
        "-c",
        type=int,
        default=5,
        help="Number of elements per smaller JSON file.",
    )
    return parser.parse_args()


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Loads and parses a JSON file.

    Args:
        file_path: The absolute or relative path to the JSON file.

    Returns:
        Dict[str, Any]: The loaded JSON object as a dictionary.

    Raises:
        FileNotFoundError: If the input file does not exist.
        json.JSONDecodeError: If the file is not a valid JSON.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_list(data_list: List[Any], chunk_size: int) -> List[List[Any]]:
    """Splits a list into smaller lists of a specified maximum size.

    Args:
        data_list: The list to be split.
        chunk_size: The maximum size of each sublist.

    Returns:
        List[List[Any]]: A list containing the chunks.
    """
    return [
        data_list[i : i + chunk_size]
        for i in range(0, len(data_list), chunk_size)
    ]


def save_chunk(
    chunk: List[Any],
    index: int,
    total_chunks: int,
    source_metadata: str,
    output_dir: str,
) -> str:
    """Saves a single chunk of VSIC data to a JSON file.

    Args:
        chunk: The list of elements to save.
        index: The 1-based index of the current chunk.
        total_chunks: The total number of chunks.
        source_metadata: The original source metadata string.
        output_dir: The target directory to write the file.

    Returns:
        str: The path to the written JSON file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate padding width based on total chunks to keep file names ordered
    padding_width = len(str(total_chunks))
    file_name = f"vsic-vn-part-{str(index).zfill(padding_width)}.json"
    output_path = os.path.join(output_dir, file_name)

    chunk_data = {
        "source": source_metadata,
        "total_vsic_count": len(chunk),
        "vsic_list": chunk,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunk_data, f, ensure_ascii=False, indent=2)

    return output_path


def split_vsic_json(input_path: str, output_dir: str, chunk_size: int) -> None:
    """Splits the input VSIC JSON file into smaller JSON files.

    Args:
        input_path: Path to the input JSON file.
        output_dir: Path to the output directory.
        chunk_size: Size of each JSON chunk.
    """
    print(f"Loading original file: {input_path}")
    try:
        data = load_json_file(input_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    source_metadata = data.get("source", "unknown")
    vsic_list = data.get("vsic_list", [])

    if not vsic_list:
        print("Warning: 'vsic_list' is empty or not found in the JSON file.")
        return

    print(f"Found {len(vsic_list)} elements in 'vsic_list'.")
    chunks = chunk_list(vsic_list, chunk_size)
    total_chunks = len(chunks)
    print(f"Splitting into {total_chunks} files (max {chunk_size} elements each)...")

    for idx, chunk in enumerate(chunks, start=1):
        saved_path = save_chunk(
            chunk=chunk,
            index=idx,
            total_chunks=total_chunks,
            source_metadata=source_metadata,
            output_dir=output_dir,
        )
        print(f"  [+] Saved: {saved_path} ({len(chunk)} elements)")

    print(f"\nSuccessfully split file! All parts saved in: {output_dir}")


def main() -> None:
    """Main execution function."""
    args = parse_arguments()
    split_vsic_json(
        input_path=args.input,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
