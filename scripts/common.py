#!/usr/bin/env python3
"""
common.py — Shared helpers for document-extractor (Python)
- logging (per-run + stdout)
- CSV writer with 5/6-column auto-detect (adds reliability when possible)
- reliability scoring
- unRAID-friendly permissions
- manual review mover
- PDF & OCR utilities used by all passes
"""
from __future__ import annotations

import csv
import logging
import os
import shutil
import statistics
import subprocess
import sys
import traceback
from typing import Iterable, List, Optional

__all__ = [
    # …whatever you already have…,
    "pdf_pages", "pdf_page_count", "pdf_page_range",
    "extract_text_layer", "sample_page_indices",
    "render_page_image", "ocr_image",
    "likely_scan_only", "score_reliability", "median",
    "get_logger", "CsvWriter", "apply_unraid_perms", "move_to_manual",
]

# ---------- logging ----------

def _attach_file_handler(log: logging.Logger, path: str, level: int) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fh = logging.FileHandler(path)
        fh.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
        ))
        fh.setLevel(level)
        log.addHandler(fh)
    except Exception:
        # last resort: print why we couldn't open the file
        print(f"[WARN] could not attach file handler to {path}", file=sys.stderr)

def get_logger(run_log: Optional[str]) -> logging.Logger:
    """
    Always logs to stdout AND to a file:
      - If run_log is given -> that file
      - Else -> /data/logs/app.log (global fallback)
    Also installs a global excepthook so uncaught errors get logged.
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }.get(level_name, logging.INFO)

    log = logging.getLogger("doc-extractor")
    if log.handlers:
        return log  # already configured

    log.setLevel(level)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    ))
    sh.setLevel(level)
    log.addHandler(sh)

    target = run_log or os.getenv("APP_LOG", "/data/logs/app.log")
    _attach_file_handler(log, target, level)

    # Global excepthook so Python tracebacks are written into the same logger
    def _log_excepthook(exc_type, exc, tb):
        try:
            log.error(
                "UNCAUGHT: %s",
                "".join(traceback.format_exception(exc_type, exc, tb)).rstrip(),
            )
        finally:
            # still send to stderr so docker logs show it too
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _log_excepthook
    return log

# ---------- perms ----------

def apply_unraid_perms(path: str) -> None:
    puid = int(os.getenv("PUID", "99"))
    pgid = int(os.getenv("PGID", "100"))
    try:
        for root, dirs, files in os.walk(path):
            for d in dirs:
                try:
                    os.chown(os.path.join(root, d), puid, pgid)
                except Exception:
                    pass
            for f in files:
                try:
                    os.chown(os.path.join(root, f), puid, pgid)
                except Exception:
                    pass
    except Exception:
        pass

# ---------- CSV (auto 5/6 columns) ----------

class CsvWriter:
    """
    If file is empty -> write 6-col header: filename,page,text,method,used_ocr,reliability
    If file exists -> detect header columns; if 5, stay 5-col but append reliability into 'method' as '|rel=X.XX'
    """
    def __init__(self, path: str, logger: Optional[logging.Logger] = None):
        self.log = logger
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._first_open = not os.path.exists(path) or os.path.getsize(path) == 0
        self._fh = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh, quoting=csv.QUOTE_ALL)

        self.cols = 6  # preferred
        if self._first_open:
            self._writer.writerow(
                ["filename", "page", "text", "method", "used_ocr", "reliability"]
            )
            self._fh.flush()
        else:
            try:
                with open(path, "r", encoding="utf-8", newline="") as rfh:
                    first = rfh.readline().strip()
                self.cols = len(next(csv.reader([first]))) if first else 6
            except Exception:
                self.cols = 6
            if self.cols == 5 and self.log:
                # warn -> warning (fix deprecated call)
                self.log.warning(
                    "CSV in legacy 5-column mode; reliability will be appended to "
                    "'method' (e.g., method|rel=0.72)."
                )

    def row(self, filename, page, text, method, used_ocr, reliability=None):
        # normalize defaults so every row has 6 real fields
        filename = str(filename or "")
        page = str(page if page is not None else "")
        text = text if isinstance(text, str) else ("" if text is None else str(text))
        method = str(method or "unknown")
        used_ocr = str(bool(used_ocr)).lower()
        reliability = 0.0 if (reliability is None or reliability == "") else float(reliability)

        self._writer.writerow(
            [filename, page, text, method, used_ocr, f"{reliability:.2f}"]
        )
        self._fh.flush()

    # Back-compat alias: newer passes call write_row(...)
    def write_row(self, filename, page, text, method, used_ocr, reliability=None):
        return self.row(filename, page, text, method, used_ocr, reliability)

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass

# ---------- reliability ----------

def score_reliability(text: str) -> float:
    """Simple alnum/length ratio in [0..1], rounded to 4 decimals."""
    if not text:
        return 0.0
    total = len(text)
    if total <= 0:
        return 0.0
    alnum = sum(ch.isalnum() for ch in text)
    s = max(0.0, min(1.0, alnum / float(total)))
    return round(s, 4)

def median(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return 0.0
    try:
        return float(statistics.median(vals))
    except Exception:
        vals.sort()
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2.0

def likely_scan_only(text_or_samples, min_chars: int = 40, rel_cap: float = 0.15) -> bool:
    """
    Heuristic: treat as 'scan-only' when there's very little text or text is very noisy.
    Accepts:
      - str: uses length + reliability ratio
      - Iterable[int]: interpreted as sample text lengths (sum is used)
      - Iterable[str]: concatenated and evaluated as text
    """
    # list/tuple of ints (lengths)
    if isinstance(text_or_samples, (list, tuple)):
        if not text_or_samples:
            return True
        first = text_or_samples[0]
        # lengths
        if isinstance(first, int):
            total = sum(int(x) for x in text_or_samples)
            return total < min_chars
        # strings -> join
        if isinstance(first, str):
            text = " ".join(text_or_samples)
        else:
            text = str(text_or_samples)
    else:
        text = text_or_samples or ""

    text = str(text)
    if len(text.strip()) < min_chars:
        return True
    return score_reliability(text) < rel_cap

# ---------- manual review ----------

def move_to_manual(file_path: str, out_dir: str, reason: str, note: str = "") -> None:
    mr = os.path.join(out_dir, "Mandatory Review")
    os.makedirs(mr, exist_ok=True)
    base = os.path.basename(file_path)
    dst = os.path.join(mr, base)
    try:
        try:
            os.replace(file_path, dst)
        except OSError:
            shutil.copy2(file_path, dst)
            try:
                os.remove(file_path)
            except Exception:
                pass
    finally:
        man = os.path.join(out_dir, "review_manifest.csv")
        with open(man, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow([base, reason, note])

# ---------- PDF helpers ----------

def _pdf_page_count_via_pdfinfo(path: str) -> int:
    try:
        out = subprocess.check_output(
            ["pdfinfo", path], stderr=subprocess.DEVNULL, text=True
        )
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return 0

def pdf_page_count(obj) -> int:
    """
    Return total page count as an INT for:
      - fitz.Document       -> .page_count
      - str path to PDF     -> PyMuPDF if available, else pdfinfo
      - int-like            -> int(obj)
    """
    # fitz.Document-like
    if hasattr(obj, "page_count"):
        try:
            return int(getattr(obj, "page_count"))
        except Exception:
            return 0

    # path
    if isinstance(obj, str):
        try:
            import fitz  # type: ignore
            try:
                with fitz.open(obj) as d:  # type: ignore
                    return int(d.page_count)
            except Exception:
                pass
        except Exception:
            pass
        return _pdf_page_count_via_pdfinfo(obj)

    # int-like
    try:
        return int(obj)
    except Exception:
        return 0

def pdf_pages(obj) -> int:
    """Back-compat wrapper used by existing passes — returns INT page count."""
    return pdf_page_count(obj)

def pdf_page_range(obj) -> range:
    """Convenience helper if you need an iterable of indices [0..n-1]."""
    return range(pdf_page_count(obj))

# ----- Text-layer extractor for a single page (0-based) ----------------------
def extract_text_layer(pdf_path: str, page_index: int) -> str:
    """Return text layer for 0-based page_index using poppler pdftotext."""
    p = int(page_index) + 1
    try:
        out = subprocess.check_output(
            ["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf_path, "-"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", "ignore").replace("\r\n", "\n").replace("\r", "\n")
    except Exception:
        return ""

# ----- Evenly-spaced sample of pages across a document -----------------------
def sample_page_indices(total_pages: int, target: int = 10):
    """
    Return a 0-based, deduped, ordered list of page indices across the doc.
    Always includes first and last when target >= 2.
    """
    n = max(1, min(int(target), int(total_pages)))
    if total_pages <= 0:
        return []
    if n == 1:
        return [0]
    step = (total_pages - 1) / (n - 1)
    idxs = sorted({int(round(i * step)) for i in range(n)})
    return [min(total_pages - 1, max(0, i)) for i in idxs]

# ---------- Rendering & OCR ----------

def render_page_image(page, dpi: int = 300, rotate: int = 0):
    """
    Render a PyMuPDF page to a grayscale Pillow image.
    Imported lazily so common.py can import even if fitz/Pillow are missing.
    """
    try:
        import fitz  # type: ignore
        from PIL import Image
    except Exception as e:
        raise RuntimeError("render_page_image requires PyMuPDF and Pillow") from e

    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    try:
        mat = mat.preRotate(rotate)  # older API
    except AttributeError:
        mat = mat.prerotate(rotate)  # newer API
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, alpha=False)
    return Image.frombytes("L", [pix.width, pix.height], pix.samples)

def ocr_image(img, lang: str = "eng", psm: int = 6, oem: int = 1) -> str:
    """
    OCR a Pillow image (or path-like) to text. Tries pytesseract, falls back to CLI.
    """
    # Try pytesseract first
    try:
        import pytesseract  # type: ignore
        return pytesseract.image_to_string(img, lang=lang, config=f"--oem {oem} --psm {psm}")
    except Exception:
        pass

    # Fallback: write to temp PNG and call tesseract CLI
    from tempfile import NamedTemporaryFile
    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError("ocr_image requires Pillow or pytesseract") from e

    if isinstance(img, Image.Image):
        with NamedTemporaryFile(suffix=".png", delete=True) as tf:
            img.save(tf.name, "PNG")
            try:
                out = subprocess.check_output(
                    [
                        "tesseract",
                        tf.name,
                        "stdout",
                        "-l",
                        lang,
                        "--oem",
                        str(oem),
                        "--psm",
                        str(psm),
                        "-c",
                        "tessedit_do_invert=1",
                    ],
                    stderr=subprocess.DEVNULL,
                )
                return out.decode("utf-8", "ignore")
            except Exception:
                return ""
    else:
        # assume it's a path-like for CLI call
        try:
            out = subprocess.check_output(
                [
                    "tesseract",
                    str(img),
                    "stdout",
                    "-l",
                    lang,
                    "--oem",
                    str(oem),
                    "--psm",
                    str(psm),
                    "-c",
                    "tessedit_do_invert=1",
                ],
                stderr=subprocess.DEVNULL,
            )
            return out.decode("utf-8", "ignore")
        except Exception:
            return ""
