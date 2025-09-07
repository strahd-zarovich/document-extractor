#!/usr/bin/env python3
"""
Pass 3 — Aggressive OCR (higher DPI, rotations, more pages).
Exit codes:
  0 = at least one page accepted
  1 = nothing acceptable
 10 = skipped (precondition)
"""
from __future__ import annotations
import os, sys, math
import fitz
from common import get_logger, CsvWriter, pdf_pages, sample_page_indices, render_page_image, ocr_image, score_reliability

OCR_B_CUTOFF = float(os.getenv("PASS_OCR_B_CUTOFF", "0.50"))
OCR_B_DPI    = int(os.getenv("OCR_B_DPI", "400"))
OCR_B_RATIO  = float(os.getenv("OCR_B_RATIO", "0.25"))
OCR_B_MAX    = int(os.getenv("OCR_B_MAX", "18"))
ROTATIONS    = [0, 90, 270]

def main(pdf_path: str, csv_out: str, _json_out: str, _out_dir: str) -> int:
    log = get_logger(os.getenv("RUN_LOG"))
    log.info(f"OCR B begin: {os.path.basename(pdf_path)}")
    base = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        log.warn(f"OCR-B skipped (open failed): {base}: {e}")
        return 10

    n = pdf_pages(doc)
    if n <= 0:
        return 1

    want = max(1, min(OCR_B_MAX, math.ceil(n * OCR_B_RATIO)))
    pages = sample_page_indices(n, want)

    cw = CsvWriter(csv_out)
    accepted = 0
    for i in pages:
        page = doc.load_page(i)
        best_txt = ""
        best_rel = 0.0
        for rot in ROTATIONS:
            try:
                img = render_page_image(page, dpi=OCR_B_DPI, rotate=rot)
                txt = ocr_image(img)
                rel = score_reliability(txt)
                if rel > best_rel:
                    best_rel, best_txt = rel, txt
                if rel >= OCR_B_CUTOFF and txt.strip():
                    break
            except Exception:
                continue
        if best_rel >= OCR_B_CUTOFF and best_txt.strip():
            cw.row(base, i+1, best_txt, "ocr_b", True)
            accepted += 1

    cw.close()
    if accepted > 0:
        log.info(f"OCR B accepted pages={accepted}")
        return 0
    log.warn("OCR B found no acceptable pages")
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
