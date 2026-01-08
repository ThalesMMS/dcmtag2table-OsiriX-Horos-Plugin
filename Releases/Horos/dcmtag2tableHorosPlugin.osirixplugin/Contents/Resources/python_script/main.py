#
# main.py
# dcmtag2table
#
# Python CLI for manifest-driven DICOM tag extraction.
#
# Thales Matheus Mendonca Santos - January 2026
#

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DEFAULT_TAGS = [
    "StudyInstanceUID",
    "StudyDescription",
    "StudyDate",
    "StudyTime",
    "AccessionNumber",
    "PatientID",
    "PatientName",
    "PatientSex",
    "PatientAge",
    "Modality",
    "SeriesInstanceUID",
    "SeriesDescription",
    "SeriesNumber",
    "ProtocolName",
    "BodyPartExamined",
    "Manufacturer",
    "ManufacturerModelName",
    "StationName",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export DICOM tags from a manifest file.")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON file")
    parser.add_argument("--output-dir", required=True, help="Directory for CSV output")
    parser.add_argument("--tags-file", default=None, help="Optional tags override file")
    parser.add_argument("--max-workers", type=int, default=4, help="Parallel workers")
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> List[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        items = data.get("series") or data.get("files") or data.get("entries")
    elif isinstance(data, list):
        items = data
    else:
        items = None

    if not items:
        raise ValueError("Manifest does not contain any series entries.")

    manifest_dir = manifest_path.parent
    file_paths = []
    for item in items:
        if isinstance(item, dict):
            path_value = item.get("file_path") or item.get("path") or item.get("filePath")
        elif isinstance(item, str):
            path_value = item
        else:
            path_value = None

        if not path_value:
            continue

        path = Path(path_value)
        if not path.is_absolute():
            path = (manifest_dir / path).resolve()
        file_paths.append(str(path))

    return file_paths


def load_tags(tags_file: Optional[str]) -> List[str]:
    if not tags_file:
        return DEFAULT_TAGS

    path = Path(tags_file).expanduser()
    if not path.exists():
        return DEFAULT_TAGS

    tags = []
    for line in path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        tags.append(trimmed)

    return tags or DEFAULT_TAGS


def ensure_output_dir(path: str) -> Path:
    output_dir = Path(path).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main() -> int:
    args = parse_args()

    try:
        manifest_path = Path(args.manifest).expanduser()
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        filelist = load_manifest(manifest_path)
        tags = load_tags(args.tags_file)
        output_dir = ensure_output_dir(args.output_dir)

        missing = [path for path in filelist if not Path(path).exists()]
        if missing:
            for path in missing:
                print(f"Missing file: {path}", file=sys.stderr)
            filelist = [path for path in filelist if Path(path).exists()]

        from dcmtag2table import dcmtag2table_from_file_list

        df = dcmtag2table_from_file_list(
            filelist,
            tags,
            max_workers=max(1, int(args.max_workers)),
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"dcmtag2table_{timestamp}.csv"
        df.to_csv(output_path, index=False)

        print(f"CSV_OUTPUT={output_path}")
        print(f"ROW_COUNT={len(df)}")
        return 0
    except Exception as exc:  # pragma: no cover - runtime guard for Horos
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
