#!/usr/bin/env python3
"""
Pass 1 — Text-layer extraction with reliability gating.
Exit codes:
  0 = accepted & CSV written
  3 = likely scan-only (let OCR try)
  5 = text too weak (let OCR try)
  4 = extraction error
"""
from __future__ import annotations
import os, sys
import fitz  # PyMuPDF
from common import (
    get_logger, CsvWriter, pdf_pages, sample_page_indices,
    likely_scan_only, score_reliability, median
)

TXT_RELIABILITY_CUTOFF = float(os.getenv("PASS_TXT_CUTOFF", "0.60"))
SAMPLES = int(os.getenv("TXT_SAMPLES", "6"))

def main(pdf_path: str, csv_out: str, _json_out: str, _out_dir: str) -> int:
    run_log = os.getenv("RUN_LOG")
    log = get_logger(run_log)
    base = os.path.basename(pdf_path)

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        log.error(f"TXT open failed: {base}: {e}")
        return 4

    n = int(pdf_pages(doc))
    if n <= 0:
        log.info("TXT summary: pages=0 chars=0 median=0.00")
        return 5

    # quick scan-only probe (sample a few pages by lengths)
    idx = sample_page_indices(n, min(3, n))
    sample_lens = []
    for i in idx:
        try:
            t = doc.load_page(i).get_text("text", sort=True)
        except Exception:
            t = ""
        sample_lens.append(len(t))

    if likely_scan_only(sample_lens):
        log.info(f"TXT skipped (scan-only likely): {base}")
        return 3

    # full text and reliability per page
    texts, lens = [], []
    for i in range(n):
        try:
            t = doc.load_page(i).get_text("text", sort=True)
        except Exception:
            t = ""
        texts.append(t)
        lens.append(len(t))

    rel = [score_reliability(t) for t in texts]
    med = median(rel)
    total_chars = sum(lens)
    log.info(f"TXT summary: pages={n} chars={total_chars} median={med:.2f}")

    if med >= TXT_RELIABILITY_CUTOFF:
        cw = CsvWriter(csv_out, logger=log)
        cw.row(base, "", "".join(texts), "pdf_text", False, reliability=med)
        cw.close()
        log.info(f"Wrote CSV for {base} (method=pdf_text, used_ocr=false)")
        return 0

    return 5

if __name__ == "__main__":
    log = get_logger(os.getenv("RUN_LOG"))
    try:
        sys.exit(main(*sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        log.exception("Unhandled error in %s", os.path.basename(__file__))
        sys.exit(1)
