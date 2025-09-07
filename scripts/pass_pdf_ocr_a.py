#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR-A pass for PDFs.
Strategy: render ~300 DPI, grayscale; Tesseract OEM=1, PSM=6; English only.
API:
  run(pdf_path, mode="per-doc"|"per-page", cutoff=0.70, logger=None)
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
import fitz  # PyMuPDF
from PIL import Image

# Try to ask MuPDF not to print its internal warnings/errors to stderr
try:
    fitz.TOOLS.mupdf_display_errors(False)  # available in many recent PyMuPDF versions
except Exception:
    try:
        fitz.TOOLS.mupdf_warnings(False)    # older / alternative API on some builds
    except Exception:
        pass

# Cache the detected signature so we only log once per process
_RENDER_SIG = None

def _render_internal(pdf_path, page_index, dpi, grayscale, logger=None):
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY if grayscale else None)
        mode = "L" if grayscale else ("RGB" if pix.alpha == 0 and pix.n >= 3 else "L")
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        return img
    finally:
        doc.close()

def _render_flex(pdf_path, page_index, dpi, grayscale, logger=None):
    """Try common signatures; if they fail, try with a fitz.Page; else fallback internally."""
    global _RENDER_SIG
    # A) (path, page_index, dpi, grayscale)
    try:
        img = common.render_page_image(pdf_path, page_index, dpi, grayscale)
        if _RENDER_SIG is None and logger:
            _RENDER_SIG = "render_page_image(path, page_index, dpi, grayscale)"
            logger.info(f"OCR-A: using {_RENDER_SIG}")
        return img
    except Exception:
        pass
    # B) (path, page_index, dpi)
    try:
        img = common.render_page_image(pdf_path, page_index, dpi)
        if grayscale:
            img = img.convert("L")
        if _RENDER_SIG is None and logger:
            _RENDER_SIG = "render_page_image(path, page_index, dpi)"
            logger.info(f"OCR A: using {_RENDER_SIG}")
        return img
    except Exception:
        pass
    # C) (path, dpi, page_index, grayscale)
    try:
        img = common.render_page_image(pdf_path, dpi, page_index, grayscale)
        if _RENDER_SIG is None and logger:
            _RENDER_SIG = "render_page_image(path, dpi, page_index, grayscale)"
            logger.info(f"OCR A: using {_RENDER_SIG}")
        return img
    except Exception:
        pass
    # D) (path, dpi, page_index)
    try:
        img = common.render_page_image(pdf_path, dpi, page_index)
        if grayscale:
            img = img.convert("L")
        if _RENDER_SIG is None and logger:
            _RENDER_SIG = "render_page_image(path, dpi, page_index)"
            logger.info(f"OCR A: using {_RENDER_SIG}")
        return img
    except Exception:
        pass
    # E) Try with a Page object (common expects 'page' not 'path')
    try:
        doc = fitz.open(pdf_path)
        try:
            page_obj = doc.load_page(page_index)
            try:
                img = common.render_page_image(page_obj, dpi, grayscale)
                if _RENDER_SIG is None and logger:
                    _RENDER_SIG = "render_page_image(page, dpi, grayscale)"
                    logger.info(f"OCR A: using {_RENDER_SIG}")
                return img
            except Exception:
                img = common.render_page_image(page_obj, dpi)
                if grayscale:
                    img = img.convert("L")
                if _RENDER_SIG is None and logger:
                    _RENDER_SIG = "render_page_image(page, dpi)"
                    logger.info(f"OCR A: using {_RENDER_SIG}")
                return img
        finally:
            doc.close()
    except Exception:
        pass
    # F) Internal fallback
    if _RENDER_SIG is None and logger:
        logger.info("OCR A: using internal renderer (fitz) due to incompatible signature")
    return _render_internal(pdf_path, page_index, dpi, grayscale, logger)

def _ocr_page(pdf_path, page_index, logger):
    # 300 DPI, grayscale for speed/quality balance
    img = _render_flex(pdf_path, page_index, 300, True, logger)
    text = common.ocr_image(img, lang="eng", psm=6, oem=1) or ""
    rel = common.score_reliability(text)
    return text, rel

def run(pdf_path: str, mode: str = "per-doc", cutoff: float = 0.70, logger=None):
    total_pages = common.pdf_page_count(pdf_path)
    if mode == "per-page":
        rows = []
        for i in range(total_pages):
            try:
                text, rel = _ocr_page(pdf_path, i, logger)
            except Exception as e:
                if logger: logger.warning(f"OCR-A error @page={i+1}: {e}")
                text, rel = "", 0.0
            rows.append({"page": i + 1, "text": text, "reliability": rel})
        med = common.median([r["reliability"] for r in rows]) if rows else 0.0
        if logger: logger.info(f"OCR A summary: pages={len(rows)} median={med:.2f} cutoff={cutoff}")
        if med >= cutoff:
            return (True, {"pages": rows})
        return (False, None)

    # per-doc: concatenate text and compute median reliability
    per_page = []
    for i in range(total_pages):
        try:
            text, rel = _ocr_page(pdf_path, i, logger)
        except Exception as e:
            if logger: logger.warning(f"OCR-A error @page={i+1}: {e}")
            text, rel = "", 0.0
        per_page.append((text, rel))
    med = common.median([r for _, r in per_page]) if per_page else 0.0
    if logger: logger.info(f"OCR A summary: pages={len(per_page)} median={med:.2f} cutoff={cutoff}")
    if med >= cutoff:
        doc_text = "\n".join(t for t, _ in per_page)
        return (True, {"text": doc_text, "reliability": med})
    return (False, None)
