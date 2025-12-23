#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized writer for document-extractor outputs.

This module is responsible for:
- Writing per-document .txt files with a simple metadata header
- Appending one index row per document to the run CSV
- Appending each document's text to one or more run-level combined
  <parent>_all_text_###.txt files with a document break, where each
  combined file stays under a configurable size limit and documents
  are never split across files.

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


def _pick_combined_path(output_root: Path, doc_text_block: str, logger: Optional[logging.Logger]) -> Path:
    """Pick the correct combined-text chunk file for appending this document.

    Rules:
    - Base name is the parent folder name (e.g., '2. Perposed Removal')
    - Files are named '<parent>_all_text_001.txt', '..._002.txt', etc.
    - Each file is kept under MAX_COMBINED_BYTES (bytes in UTF-8)
    - A document is never split across files: if it doesn't fit, we start a new file.
    """
    # Maximum size per combined file in bytes (approx. "characters").
    max_bytes_default = 3_000_000  # ~3 MB is well under current ChatGPT limits.
    try:
        max_bytes = int(os.getenv("MAX_COMBINED_BYTES", str(max_bytes_default)))
    except Exception:
        max_bytes = max_bytes_default

    # Base name derived from the run folder (parent directory of the CSV).
    parent_name = output_root.name or "all_text"
    prefix = f"{parent_name}_all_text"

    # Size of this document when encoded as UTF-8.
    doc_bytes = len(doc_text_block.encode("utf-8"))

    # Find existing chunk files for this run.
    existing = sorted(output_root.glob(f"{prefix}_*.txt"))

    if not existing:
        # No combined files yet; start with _001.
        return output_root / f"{prefix}_001.txt"

    # Use the highest-numbered existing chunk.
    current = existing[-1]
    try:
        current_size = current.stat().st_size
    except FileNotFoundError:
        current_size = 0

    # If it fits in the current chunk, reuse it; otherwise start a new one.
    if current_size + doc_bytes <= max_bytes:
        return current

    # Need a new chunk. Try to parse the numeric suffix; if that fails,
    # just increment based on count.
    stem = current.stem  # e.g. '2. Perposed Removal_all_text_003'
    parts = stem.rsplit("_", 1)
    idx = len(existing)
    if len(parts) == 2:
        try:
            idx = int(parts[1])
        except ValueError:
            # fall back to count-based index
            idx = len(existing)

    new_idx = idx + 1
    return output_root / f"{prefix}_{new_idx:03d}.txt"


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
    """Write the .txt (if any), append to combined all_text_###.txt, and append one row to the run CSV.

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

    # Output root (per-run folder, e.g. /.../output/2. Perposed Removal)
    output_root = csv_path_obj.parent

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

        # Build the full document content (header + page markers + text),
        # so we can write it once to the per-doc .txt and also append it to a combined file.
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

        content_lines = []
        # Header
        content_lines.extend(header_lines)
        content_lines.append("")  # blank line between header and content

        # Pages
        for page_num, text in pages:
            content_lines.append(f"=== [PAGE {page_num}] ===")
            content_lines.append("")  # blank line after page marker
            if text:
                content_lines.append(str(text))
            content_lines.append("")  # blank line after page content

        # Final content string for this document (atomic unit for chunking)
        doc_text_block = "\n".join(content_lines) + "\n"

        # Write the per-document .txt file (unchanged behavior)
        _ensure_parent(txt_path)
        try:
            with txt_path.open("w", encoding="utf-8", newline="") as f:
                f.write(doc_text_block)

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

        # Append to the appropriate combined all_text_###.txt with a clear document break.
        try:
            combined_txt_path = _pick_combined_path(output_root, doc_text_block, logger)
            _ensure_parent(combined_txt_path)
            with combined_txt_path.open("a", encoding="utf-8", newline="") as cf:
                cf.write(doc_text_block)
                cf.write("----- DOCUMENT BREAK -----\n\n")

            try:
                os.chmod(combined_txt_path, 0o664)
            except Exception:
                pass

        except Exception as e:
            if logger:
                logger.error(f"Failed to append to combined text file for {orig_path}: {e}")

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
