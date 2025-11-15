#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized writer for document-extractor outputs.

This module is responsible for:
- Writing per-document .txt files with a simple metadata header
- Appending one index row per document to the run CSV

Pass scripts should call write_result(...) exactly once per source document.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, Tuple
import logging


Page = Tuple[int, str]


def _ensure_parent(path: Path) -> None:
    """Create parent directories for a path if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _compute_paths(original_file: str, csv_path: str) -> Tuple[Path, str, Path, Path, Path]:
    """Return (orig_path, relative_path, txt_root, txt_relative_path, txt_path).

    - orig_path: absolute Path to the original file
    - relative_path: str path of orig_path relative to INPUT_DIR (or just filename on failure)
    - txt_root: Path to the /data/output/txt root inferred from the CSV path
    - txt_relative_path: Path object for the relative .txt path under txt_root
    - txt_path: full Path to the .txt file
    """
    orig_path = Path(original_file).resolve()

    # Derive the relative path under INPUT_DIR, but fall back gracefully if env is weird.
    input_root = Path(os.getenv("INPUT_DIR", "/data/input")).resolve()
    try:
        relative_path = str(orig_path.relative_to(input_root))
    except Exception:
        # Fallback: keep just the filename so we never crash on a misconfigured INPUT_DIR.
        relative_path = orig_path.name

    csv_path_obj = Path(csv_path).resolve()
    output_root = csv_path_obj.parent
    txt_root = output_root / "txt"

    txt_relative_path = Path(relative_path).with_suffix(".txt")
    txt_path = txt_root / txt_relative_path

    return orig_path, relative_path, txt_root, txt_relative_path, txt_path


def write_result(
    csv_path: str,
    original_file: str,
    pages: Sequence[Page],
    pass_used: str,
    score: float,
    status: str,
    used_ocr: bool,
    logger: Optional[logging.Logger] = None,
    notes: str = "",
) -> None:
    """Write the .txt (if any) and append one row to the run CSV.

    - csv_path: path to the per-run CSV (created/seeded by process_run.py)
    - original_file: absolute path to the source file under /data/input
    - pages: sequence of (page_number, text) tuples; if empty or all-blank, no .txt is written
    - pass_used: name of the winning pass (pdf_text, pdf_ocr_a, img_ocr, docx, etc.)
    - score: overall reliability score for the chosen result
    - status: OK, MANDATORY_REVIEW, ERROR, etc.
    - used_ocr: True if the winning result used OCR
    - notes: optional free-form text for the CSV notes column
    """
    csv_path_obj = Path(csv_path).resolve()
    orig_path, relative_path, txt_root, txt_relative_path, txt_path = _compute_paths(
        original_file, str(csv_path_obj)
    )

    # Common fields
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = csv_path_obj.stem

    # Determine whether we actually have usable text
    has_text = False
    for _, text in pages:
        if text and str(text).strip():
            has_text = True
            break

    pages_count = len(pages)

    txt_relative_str = ""
    if has_text:
        txt_relative_str = str(txt_relative_path)

        # Write the .txt file with header + page markers
        _ensure_parent(txt_path)
        try:
            with txt_path.open("w", encoding="utf-8", newline="") as f:
                header_lines = [
                    f"# original_file: {orig_path}",
                    f"# original_name: {orig_path.name}",
                    f"# relative_path: {relative_path}",
                    f"# pages: {pages_count}",
                    f"# processed_at: {processed_at}",
                    f"# pass_used: {pass_used}",
                    f"# score: {score}",
                    f"# status: {status}",
                ]
                for line in header_lines:
                    f.write(line + "\n")
                f.write("\n")  # blank line between header and content

                for page_num, text in pages:
                    f.write(f"=== [PAGE {page_num}] ===\n\n")
                    if text:
                        f.write(str(text))
                    f.write("\n\n")

            # Try to keep permissions unRAID-friendly; ignore failures.
            try:
                os.chmod(txt_path, 0o664)
            except Exception:
                pass

        except Exception as e:
            if logger:
                logger.error(f"Failed to write text file for {orig_path}: {e}")
            # If the text file fails, we still record the CSV row but leave txt_relative_path blank.
            txt_relative_str = ""

    # Append one row to the run CSV (header is created by process_run.py)
    try:
        _ensure_parent(csv_path_obj)
        with csv_path_obj.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(
                [
                    str(orig_path),
                    orig_path.name,
                    relative_path,
                    txt_relative_str,
                    pages_count,
                    processed_at,
                    pass_used,
                    f"{float(score):.2f}" if score is not None else "",
                    status,
                    str(bool(used_ocr)).lower(),
                    run_id,
                    notes or "",
                ]
            )
        try:
            os.chmod(csv_path_obj, 0o664)
        except Exception:
            pass
    except Exception as e:
        if logger:
            logger.error(f"Failed to append CSV row for {orig_path}: {e}")
