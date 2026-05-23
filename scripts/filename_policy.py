#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filename_policy.py

v0.1.9 helper for safe output filenames.

Purpose:
- sanitize filenames for Windows / SMB / UnRAID compatibility
- prevent very long embedded portfolio names from becoming unusable
- preserve file extensions when shortening
- add a short hash so truncated names remain traceable and collision-resistant

This module should not move files or write manifests.
It only decides safe names.
"""

from __future__ import annotations

import hashlib
import os

# Conservative default.
# Keeps room for parent folders in Windows/SMB paths.
DEFAULT_MAX_FILENAME_LEN = 180


def sanitize_filename(name: str) -> str:
    """
    Replace filesystem-problem characters with underscores.

    This intentionally keeps spaces and most readable characters.
    """
    name = str(name or "").strip()

    if not name:
        name = "unknown_file"

    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")

    # Avoid repeated ugly separators from sanitizing.
    while "__" in name:
        name = name.replace("__", "_")

    return name


def short_hash(value: str, length: int = 8) -> str:
    """
    Return a short stable hash for collision resistance and traceability.
    """
    value = str(value or "")
    return hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()[:length]


def limit_filename_length(name: str, max_len: int = DEFAULT_MAX_FILENAME_LEN) -> str:
    """
    Limit a filename while preserving the extension.

    Example:
        VeryLongName.xlsx
        -> VeryLongName_TRUNC_a1b2c3d4.xlsx

    If the name is already short enough, it is returned unchanged.
    """
    name = sanitize_filename(name)

    if len(name) <= max_len:
        return name

    stem, ext = os.path.splitext(name)
    digest = short_hash(name)

    marker = f"_TRUNC_{digest}"

    # Leave room for marker + extension.
    keep_len = max_len - len(marker) - len(ext)

    # Safety floor.
    if keep_len < 20:
        keep_len = 20

    shortened = f"{stem[:keep_len]}{marker}{ext}"

    # Final guard in case extension or marker math gets weird.
    if len(shortened) > max_len:
        shortened = shortened[:max_len - len(ext)] + ext

    return shortened


def safe_output_filename(name: str, max_len: int = DEFAULT_MAX_FILENAME_LEN) -> str:
    """
    Main public helper.

    Use this anywhere the project needs a final physical filename.
    """
    return limit_filename_length(name, max_len=max_len)


if __name__ == "__main__":
    # Simple manual test:
    sample = "Parent.pdf__Very Long Child Name " * 20 + ".xlsx"
    print(safe_output_filename(sample))