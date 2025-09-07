#!/usr/bin/env python3
"""
Pass 2 — Quick OCR on a limited set of weak pages (lower DPI).
Exit codes:
  0 = at least one page accepted & CSV rows written
  1 = nothing acceptable
 10 = skipped (precondition)
"""
from __future__ import annotations
import os, sys, math
import fitz
from common import get_logger, CsvWriter, pdf_pages, sample_page_indices, render_page_image, ocr_image, score_reliability

OCR_A_CUTOFF = float(os.getenv("PASS_OCR_A_CUTOFF", "0.55"))
OCR_A_DPI    = int(os.getenv("OCR_A_DPI", "300"))
OCR_A_RATIO  = float(os.getenv("OCR_A_RATIO", "0.15"))   # try 15% of pages
OCR_A_MAX    = int(os.getenv("OCR_A_MAX", "12"))

def main(pdf_path: str, csv_out: str, _json_out: str, _out_dir: str) -> int:
    log = get_logger(os.getenv("RUN_LOG"))
    base = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        log.warn(f"OCR-A skipped (open failed): {base}: {e}")
        return 10

    n = pdf_pages(doc)
    if n <= 0:
        return 1

    want = max(1, min(OCR_A_MAX, math.ceil(n * OCR_A_RATIO)))
    pages = sample_page_indices(n, want)

    cw = CsvWriter(csv_out)
    accepted = 0
    for i in pages:
        try:
            img = render_page_image(doc.load_page(i), dpi=OCR_A_DPI)
            txt = ocr_image(img)
            rel = score_reliability(txt)
            if rel >= OCR_A_CUTOFF and txt.strip():
                cw.row(base, i+1, txt, "ocr_a", True)
                accepted += 1
        except Exception:
            continue

    cw.close()
    if accepted > 0:
        log.info(f"OCR A accepted pages={accepted}")
        return 0
    return 1

if __name__ == "__main__":
    import sys, os
    from common import get_logger
    # Use RUN_LOG when present, else global fallback file
    log = get_logger(os.getenv("RUN_LOG"))
    try:
        sys.exit(main(*sys.argv[1:]))
    except SystemExit as e:
        raise
    except Exception:
        log.exception("Unhandled error in %s", os.path.basename(__file__))
        sys.exit(1)
