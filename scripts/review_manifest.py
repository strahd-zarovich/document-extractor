#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review_manifest.py

v0.1.9 helper for writing Manual Review manifests.

Purpose:
- centralize review_manifest.csv writing
- standardize columns
- preserve forensic lineage metadata
- keep process_run.py from owning manifest formatting details

This module should not move files.
It only writes manifest rows.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

from lineage import build_lineage_metadata


REVIEW_MANIFEST_HEADER = [
    "filename",
    "reason",
    "portfolio_path",
    "original_full_name",
]


def normalize_reason(reason: str) -> str:
    """
    Convert messy/internal reasons into consistent review reason labels.
    """
    reason = str(reason or "").strip()

    if not reason:
        return "unknown"

    lowered = reason.lower()

    if lowered.startswith("pass rc="):
        return "pass_rc"

    if lowered in {"unsupported", "unsupported_ext"}:
        return "unsupported_ext"

    if lowered in {"manual_review", "manual_review_ext"}:
        return "manual_review_ext"

    if "low" in lowered and "disk" in lowered:
        return "low_workdir_space"

    if "spreadsheet" in lowered:
        return "spreadsheet_manual_review"

    if "doc" in lowered and "manual" in lowered:
        return "doc_manual_review"

    if "timeout" in lowered:
        return "timeout"

    if "embedded" in lowered:
        return "embedded_extract_failure"

    return lowered.replace(" ", "_")


def write_review_row(
    out_dir: str | Path,
    filename: str,
    reason: str,
    original_full_name: str = "",
    source_path: str = "",
    metadata: Optional[Dict[str, object]] = None,
) -> Path:
    """
    Append one row to review_manifest.csv.

    out_dir:
        Run output directory.

    filename:
        Final physical filename in Mandatory Review.

    reason:
        Standard or raw reason. This function normalizes it.

    original_full_name:
        Full generated name before truncation, if available.

    source_path:
        Original source path, if useful.

    metadata:
        Optional lineage metadata from lineage.py.
    """
    out_dir = Path(out_dir)
    manifest = out_dir / "review_manifest.csv"
    new_file = not manifest.exists()

    if metadata is None:
        metadata = build_lineage_metadata(
            physical_name=filename,
            original_full_name=original_full_name or filename,
            source_path=source_path,
        )

    norm_reason = normalize_reason(reason)

    with manifest.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        if new_file:
            w.writerow(REVIEW_MANIFEST_HEADER)

        w.writerow([
            filename,
            norm_reason,
            metadata.get("portfolio_path", ""),
            metadata.get("original_full_name", original_full_name or filename),
        ])

    try:
        manifest.chmod(0o664)
    except Exception:
        pass

    return manifest


if __name__ == "__main__":
    print(normalize_reason("pass rc=1"))
    print(normalize_reason("unsupported"))