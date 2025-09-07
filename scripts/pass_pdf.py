#!/usr/bin/env python3
"""
Orchestrate PDF extraction:
1) TXT (text layer) — accept if reliable
2) OCR-A
3) OCR-B (always attempt if TXT didn't accept)
Success if any pass returns 0.
Exit codes: 0=accepted; 1=none accepted
"""
from __future__ import annotations
import os, sys, subprocess
from common import get_logger

def _run(argv) -> int:
    try:
        return subprocess.call(argv)
    except Exception:
        return 1

def main(pdf_path: str, csv_out: str, json_out: str, out_dir: str) -> int:
    log = get_logger(os.getenv("RUN_LOG"))
    base = os.path.basename(pdf_path)
    log.info(f"PDF start: {base} (size={os.path.getsize(pdf_path)}B)")

    # 1) TXT (text layer)
    rc_txt = _run(["/app/scripts/pass_pdf_txt.sh", pdf_path, csv_out, json_out, out_dir])
    if rc_txt == 0:
        # TXT accepted → done
        return 0

    # 2) OCR-A (always try when TXT didn't accept)
    log.info(f"OCR A begin: {base}")
    rc_a = _run(["/app/scripts/pass_pdf_ocr_a.sh", pdf_path, csv_out, json_out, out_dir])

    # 3) OCR-B (always try as second chance)
    log.info(f"OCR B begin: {base}")
    rc_b = _run(["/app/scripts/pass_pdf_ocr_b.sh", pdf_path, csv_out, json_out, out_dir])

    # Accept if any pass succeeded
    if rc_a == 0 or rc_b == 0:
        return 0

    # None accepted → let caller move to Manual Review
    return 1

if __name__ == "__main__":
    log = get_logger(os.getenv("RUN_LOG"))
    try:
        sys.exit(main(*sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        log.exception("Unhandled error in %s", os.path.basename(__file__))
        sys.exit(1)
