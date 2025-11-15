#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize a .txt file into one CSV row with reliability score.
Args:
  1: path to .txt
  2: path to CSV for this run
  3: path to run.log
Env:
  LOG_LEVEL (INFO/DEBUG), optional
"""
import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import common
import output_writer

def main():
    if len(sys.argv) < 4:
        print("usage: pass_txt.py <txt_path> <csv_path> <run_log_path>", file=sys.stderr)
        sys.exit(2)

    txt_path, csv_path, run_log_path = sys.argv[1], sys.argv[2], sys.argv[3]
    logger = common.get_logger(run_log_path)

    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        logger.error(f"TXT open failed: {os.path.basename(txt_path)} :: {e}")
        sys.exit(1)

    rel = common.score_reliability(text)

    # Build pages list — treat the whole TXT as a single "page 1"
    pages = [(1, text)] if text.strip() else []
    status = "OK" if pages else "ERROR"

    # Use centralized writer to create .txt (if any) and append CSV row
    output_writer.write_result(
        csv_path=csv_path,
        original_file=os.path.abspath(txt_path),
        pages=pages,
        pass_used="txt",
        score=rel,
        status=status,
        used_ocr=False,
        logger=logger,
    )

    if status == "OK":
        logger.info(f"TXT file accepted: {os.path.basename(txt_path)} reliability={rel:.2f}")
    else:
        logger.warning(f"TXT file had no usable text: {os.path.basename(txt_path)}")

    sys.exit(0)

if __name__ == "__main__":
    main()
