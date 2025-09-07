#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract native text layer from PDF; compute reliability; decide accept vs escalate.
API:
  run(pdf_path, mode="per-doc"|"per-page", cutoff=0.80, logger=None)
Returns:
  (True, payload) on accept; (False, None) on reject.
  payload per-doc: {"text": str, "reliability": float}
  payload per-page: {"pages": [{"page": int, "text": str, "reliability": float}, ...]}
"""
import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import common

def _per_page(pdf_path, logger):
    total_pages = common.pdf_page_count(pdf_path)
    pages = []
    for i in range(total_pages):
        try:
            text = common.extract_text_layer(pdf_path, i) or ""
        except Exception as e:
            if logger: logger.warning(f"TXT extract error @page={i+1}: {e}")
            text = ""
        rel = common.score_reliability(text)
        pages.append({"page": i + 1, "text": text, "reliability": rel})
    return pages

def run(pdf_path: str, mode: str = "per-doc", cutoff: float = 0.80, logger=None):
    total_pages = common.pdf_page_count(pdf_path)

    # Quick triage (optional): if clearly scan-only, short-circuit to OCR by returning reject
    # Use project's helper if present
    try:
        sample_idxs = common.sample_page_indices(total_pages, target=min(6, total_pages))
        samples = []
        for idx in sample_idxs:
            try:
                t = common.extract_text_layer(pdf_path, idx) or ""
            except Exception:
                t = ""
            samples.append(t)
        if hasattr(common, "likely_scan_only") and common.likely_scan_only(samples):
            if logger: logger.info("TXT triage: likely scan-only -> reject to OCR")
            return (False, None)
    except Exception:
        pass  # sampling is best-effort

    # Full extraction
    pages = _per_page(pdf_path, logger)
    if mode == "per-page":
        # accept only if median(page rel) meets cutoff
        med = common.median([p["reliability"] for p in pages]) if pages else 0.0
        if logger: logger.info(f"TXT summary: pages={len(pages)} median={med:.2f} cutoff={cutoff}")
        if med >= cutoff:
            return (True, {"pages": pages})
        return (False, None)

    # per-doc: concatenate text, compute overall median reliability
    doc_text = "\n".join(p["text"] for p in pages)
    med = common.median([p["reliability"] for p in pages]) if pages else 0.0
    if logger: logger.info(f"TXT summary: pages={len(pages)} median={med:.2f} cutoff={cutoff}")
    if med >= cutoff:
        return (True, {"text": doc_text, "reliability": med})
    return (False, None)
