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

def main():
    if len(sys.argv) < 4:
        print("usage: pass_txt.py <txt_path> <csv_path> <run_log_path>", file=sys.stderr)
        sys.exit(2)

    txt_path, csv_path, run_log_path = sys.argv[1], sys.argv[2], sys.argv[3]
    logger = common.get_logger(run_log_path)
    writer = common.CsvWriter(csv_path)

    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        logger.error(f"TXT open failed: {os.path.basename(txt_path)} :: {e}")
        sys.exit(1)

    rel = common.score_reliability(text)
    writer.write_row(os.path.basename(txt_path), "-", text, "txt", "false", f"{rel:.2f}")
    logger.info(f"TXT file accepted: {os.path.basename(txt_path)} reliability={rel:.2f}")
    sys.exit(0)

if __name__ == "__main__":
    main()
