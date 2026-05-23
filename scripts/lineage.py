#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lineage.py

v0.1.9 helper for forensic parent-child lineage.

Purpose:
- preserve portfolio / embedded attachment paths
- keep forensic traceability outside the physical filename
- support shortened filenames from filename_policy.py
- provide metadata for TXT headers, review manifests, and future JSON sidecars

This module does not move files, rename files, or write output files.
It only builds lineage metadata.
"""

from __future__ import annotations

import os
from typing import Dict, List


LINEAGE_SEPARATOR = "__"


def split_lineage_name(name: str) -> List[str]:
    """
    Split a generated embedded filename into lineage parts.

    Example:
        Parent.pdf__Email.pdf__Attachment.xlsx

    Returns:
        [
            "Parent.pdf",
            "Email.pdf",
            "Attachment.xlsx"
        ]
    """
    name = os.path.basename(str(name or "")).strip()

    if not name:
        return []

    parts = [p.strip() for p in name.split(LINEAGE_SEPARATOR) if p.strip()]
    return parts


def portfolio_path(name: str, separator: str = " / ") -> str:
    """
    Return a readable forensic path.

    Example:
        Parent.pdf / Email.pdf / Attachment.xlsx
    """
    parts = split_lineage_name(name)

    if not parts:
        return ""

    return separator.join(parts)


def build_lineage_metadata(
    physical_name: str,
    original_full_name: str = "",
    source_path: str = "",
) -> Dict[str, object]:
    """
    Build a small metadata dictionary for forensic traceability.

    physical_name:
        The final filesystem-safe output filename.

    original_full_name:
        The pre-truncated/generated full name, if available.

    source_path:
        Optional full path to source file before movement.
    """
    physical_name = os.path.basename(str(physical_name or "")).strip()
    original_full_name = os.path.basename(str(original_full_name or physical_name)).strip()

    parts = split_lineage_name(original_full_name)

    return {
        "physical_name": physical_name,
        "original_full_name": original_full_name,
        "portfolio_path": " / ".join(parts),
        "lineage_parts": parts,
        "source_path": str(source_path or ""),
    }


def format_txt_header(metadata: Dict[str, object]) -> str:
    """
    Return a plain text metadata block suitable for top-of-file TXT output.
    """
    physical_name = metadata.get("physical_name", "")
    original_full_name = metadata.get("original_full_name", "")
    portfolio_path_value = metadata.get("portfolio_path", "")
    source_path = metadata.get("source_path", "")

    lines = [
        "=== DOCUMENT METADATA ===",
        f"Output Name: {physical_name}",
        f"Original Full Name: {original_full_name}",
        f"Portfolio Path: {portfolio_path_value}",
    ]

    if source_path:
        lines.append(f"Source Path: {source_path}")

    lines.append("===")

    return "\n".join(lines)


if __name__ == "__main__":
    sample = "Parent.pdf__Email.pdf__Attachment.xlsx"
    meta = build_lineage_metadata(
        physical_name="Parent_TRUNC_a1b2c3d4.xlsx",
        original_full_name=sample,
    )
    print(format_txt_header(meta))