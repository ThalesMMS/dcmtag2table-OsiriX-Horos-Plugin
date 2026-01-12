#!/usr/bin/env python3
"""
Build inverted index JSON files from a dcmtag2table CSV export.

Each tag in the tags file becomes its own JSON file mapping:
  <tag value> -> [StudyInstanceUID, ...]
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set


MISSING_TOKENS = {
    "",
    "Not found",
    "None",
    "none",
    "NULL",
    "null",
    "nan",
    "NaN",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build inverted indexes from a dcmtag2table CSV export."
    )
    parser.add_argument("--csv", required=True, help="Path to CSV exported by the plugin")
    parser.add_argument("--tags-file", required=True, help="Path to dicomtags.txt")
    parser.add_argument("--output-dir", required=True, help="Directory for JSON output")
    parser.add_argument(
        "--study-uid-column",
        default="StudyInstanceUID",
        help="CSV column name used as the index key",
    )
    parser.add_argument(
        "--missing-token",
        action="append",
        default=[],
        help="Extra token to treat as missing (can be repeated)",
    )
    return parser.parse_args()


def load_tags(path: Path) -> List[str]:
    tags = []
    for line in path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        tags.append(trimmed)
    return tags


def sanitize_filename(tag: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", tag).strip("._")
    return safe or "tag"


def build_indexes(
    csv_path: Path,
    tags: Iterable[str],
    study_uid_column: str,
    missing_tokens: Set[str],
) -> Dict[str, Dict[str, Set[str]]]:
    indexes: Dict[str, Dict[str, Set[str]]] = {
        tag: defaultdict(set) for tag in tags
    }

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV file has no header row.")

        missing_tags = [tag for tag in tags if tag not in reader.fieldnames]
        if missing_tags:
            raise ValueError(
                "CSV is missing tag columns: " + ", ".join(sorted(missing_tags))
            )

        if study_uid_column not in reader.fieldnames:
            raise ValueError(
                f"CSV is missing required column: {study_uid_column}"
            )

        for row in reader:
            study_uid = (row.get(study_uid_column) or "").strip()
            if study_uid in missing_tokens:
                continue

            for tag in tags:
                raw_value = row.get(tag)
                if raw_value is None:
                    continue
                value = raw_value.strip()
                if value in missing_tokens:
                    continue
                indexes[tag][value].add(study_uid)

    return indexes


def write_indexes(
    output_dir: Path, indexes: Dict[str, Dict[str, Set[str]]]
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    index_manifest: Dict[str, List[str]] = {}

    for tag, value_map in indexes.items():
        filename = f"{sanitize_filename(tag)}.json"
        output_path = output_dir / filename
        serializable = {
            value: sorted(uids) for value, uids in value_map.items()
        }
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(serializable, handle, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"WROTE={output_path}")
        index_manifest[filename] = sorted(value_map.keys())

    index_path = output_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(index_manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"WROTE={index_path}")


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).expanduser()
    tags_path = Path(args.tags_file).expanduser()
    output_dir = Path(args.output_dir).expanduser()

    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1
    if not tags_path.exists():
        print(f"ERROR: Tags file not found: {tags_path}", file=sys.stderr)
        return 1

    tags = load_tags(tags_path)
    if not tags:
        print("ERROR: Tags file is empty.", file=sys.stderr)
        return 1

    missing_tokens = set(MISSING_TOKENS)
    missing_tokens.update(token.strip() for token in args.missing_token)

    try:
        indexes = build_indexes(
            csv_path=csv_path,
            tags=tags,
            study_uid_column=args.study_uid_column,
            missing_tokens=missing_tokens,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    write_indexes(output_dir, indexes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
