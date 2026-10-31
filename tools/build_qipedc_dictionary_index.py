"""Build a provenance-first index of the official QIPEDC dictionary export.

The generated index is a research/catalogue artifact.  It does not copy the
source videos, assign recognizer class IDs, or promote a dictionary entry to
the avatar runtime.  QIPEDC word-level records and the local All_cam1
recognizer collection are intentionally kept in separate namespaces.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = (
    ROOT.parents[1] / "ver 1 - 2025-04-18 - VSL" / "qipedc_dictionary_4362_records.json",
    ROOT.parent / "qipedc_dictionary_4362_records.json",
)
OUTPUT = ROOT / "research" / "qipedc-dictionary-index.json"
SOURCE_URL = "https://qipedc.moet.gov.vn/dictionary"


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def folded(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def find_source(explicit: Path | None) -> Path:
    candidates = (explicit,) if explicit else DEFAULT_SOURCES
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    searched = ", ".join(str(item) for item in candidates)
    raise FileNotFoundError(f"QIPEDC JSON export not found; searched: {searched}")


def load_records(path: Path) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("The QIPEDC export must contain a JSON list")
    required = {"_id", "word", "video_url"}
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not required.issubset(record):
            raise ValueError(f"QIPEDC record {index} is missing one of {sorted(required)}")
    return records


def build_index(source: Path, records: list[dict]) -> dict:
    terms: dict[str, dict] = {}
    raw_terms: set[str] = set()
    region_counts: Counter[str] = Counter()
    ids: set[str] = set()
    entries: list[dict] = []
    for record in records:
        source_id = str(record["_id"])
        if source_id in ids:
            raise ValueError(f"Duplicate QIPEDC source ID: {source_id}")
        ids.add(source_id)
        word = str(record["word"])
        raw_terms.add(word)
        key = folded(word)
        region = str(record.get("inferred_region") or "Không xác định")
        region_counts[region] += 1
        terms.setdefault(key, {"word": word, "source_ids": [], "regions": set()})
        terms[key]["source_ids"].append(source_id)
        terms[key]["regions"].add(region)
        entries.append(
            {
                "source_id": source_id,
                "word": word,
                "normalized_word": key,
                "description": record.get("description") or "",
                "part_of_speech": record.get("tl"),
                "type": record.get("type"),
                "inferred_region": region,
                "video_url": record["video_url"],
                "thumbnail_url": record.get("thumbnail_url"),
                "illustration_url": record.get("illustration_url") or None,
            }
        )
    unique_terms = []
    for value in sorted(terms.values(), key=lambda item: item["word"].casefold()):
        unique_terms.append(
            {
                "word": value["word"],
                "normalized_word": folded(value["word"]),
                "source_ids": sorted(value["source_ids"]),
                "regions": sorted(value["regions"]),
                "entry_count": len(value["source_ids"]),
            }
        )
    return {
        "schema": "clinic-qipedc-dictionary-index-v1",
        "source": {
            "name": "QIPEDC official dictionary export",
            "organization": "Ministry of Education and Training, Vietnam",
            "kind": "official-dictionary-catalogue",
            "url": SOURCE_URL,
            "local_export": str(source),
            "local_export_sha256": digest(source),
            "redistribution": "index metadata only; source videos remain external",
        },
        "counts": {
            "video_entries": len(entries),
            "raw_unique_terms": len(raw_terms),
            "normalized_unique_terms": len(unique_terms),
            "region_entry_counts": dict(sorted(region_counts.items())),
        },
        "crosswalk_policy": {
            "recognizer_namespace": "All_cam1 400-class model",
            "rule": "QIPEDC source IDs are not recognizer class IDs; matching labels require explicit sense, movement and signer review",
            "automatic_model_id_assignment": False,
        },
        "entries": entries,
        "terms": unique_terms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, help="Path to a local QIPEDC JSON export")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Index path")
    args = parser.parse_args()
    source = find_source(args.dictionary)
    index = build_index(source, load_records(source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "counts": index["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
