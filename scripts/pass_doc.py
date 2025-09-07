#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOC/DOCX pass:
 - Extracts native text from .docx (python-docx) and .doc (antiword -> catdoc fallback)
 - Computes reliability and writes a single CSV row (per-document)
 - Accepts if reliability >= PASS_DOC_CUTOFF (default 0.75); else returns non-zero to trigger quarantine

Args:
  1: path to DOC/DOCX file
  2: path to CSV for this run
  3: path to run.log

Env:
  PASS_DOC_CUTOFF (float, default 0.75)
  LOG_LEVEL (INFO/DEBUG), optional
"""
import os
import sys
import subprocess
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import common  # shared logger, CsvWriter, score_reliability

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

def _docx_text(path: str) -> str:
    # Extract paragraphs + table cell text
    try:
        import docx  # python-docx
    except Exception as e:
        raise RuntimeError(f"python-docx not available: {e}")

    try:
        d = docx.Document(path)
    except Exception as e:
        raise RuntimeError(f"docx open failed: {e}")

    parts = []
    # paragraphs
    for p in d.paragraphs:
        if p.text:
            parts.append(p.text)
    # tables
    for t in d.tables:
        try:
            for row in t.rows:
                for cell in row.cells:
                    if cell.text:
                        parts.append(cell.text)
        except Exception:
            # table iteration is best-effort
            pass
    return "\n".join(parts)

def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def _doc_text(path: str) -> str:
    # Prefer antiword; fallback to catdoc if present
    try:
        cp = _run_cmd(["antiword", path])
        if cp.returncode == 0 and cp.stdout:
            return cp.stdout
    except FileNotFoundError:
        pass  # antiword not installed

    # Fallback: catdoc
    try:
        cp = _run_cmd(["catdoc", path])
        if cp.returncode == 0 and cp.stdout:
            return cp.stdout
    except FileNotFoundError:
        pass

    raise RuntimeError("Neither antiword nor catdoc produced text")

def main():
    if len(sys.argv) < 4:
        print("usage: pass_doc.py <doc|docx_path> <csv_path> <run_log_path>", file=sys.stderr)
        sys.exit(2)

    in_path, csv_path, run_log_path = sys.argv[1], sys.argv[2], sys.argv[3]
    basename = os.path.basename(in_path)
    ext = os.path.splitext(in_path)[1].lower()

    logger = common.get_logger(run_log_path)
    writer = common.CsvWriter(csv_path)

    cutoff = _env_float("PASS_DOC_CUTOFF", 0.75)

    # Extract
    try:
        if ext == ".docx":
            method = "docx_text"
            text = _docx_text(in_path)
        elif ext == ".doc":
            method = "doc_text"
            text = _doc_text(in_path)
        else:
            logger.error(f"pass_doc called with unsupported extension: {ext}")
            sys.exit(2)
    except Exception as e:
        logger.error(f"DOC open/extract failed: {basename} :: {e}")
        sys.exit(1)

    # Reliability (per-document)
    rel = common.score_reliability(text or "")
    logger.info(f"DOC summary: {basename} method={method} reliability={rel:.2f} cutoff={cutoff}")

    # Gate & write
    if rel >= cutoff and (text or "").strip():
        writer.write_row(basename, "-", text, method, "false", f"{rel:.2f}")
        logger.info(f"DOC accept: {basename} reliability={rel:.2f}")
        sys.exit(0)

    logger.warning(f"DOC below cutoff: {basename} reliability={rel:.2f} < {cutoff}")
    sys.exit(1)

if __name__ == "__main__":
    main()
