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
        # v0.1.4: ensure run.log is group-writable
        try:
            os.chmod(path, 0o664)
        except Exception:
            pass
    except Exception:
        # last resort: print why we couldn't open the file
        print(f"[WARN] could not attach file handler to {path}", file=sys.stderr)

# v0.1.4: ensure run.log is group-writable (UnRAID-friendly)
try:
    os.chmod(path, 0o664)   # if your variable is named 'target', use that name
except Exception:
    pass

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

def has_workdir_space(work_dir: str, min_bytes: int = 1 << 30) -> bool:
    """
    Return True if work_dir has at least min_bytes free (default ~1GB).
    On error, be permissive (return True) to avoid false negatives.
    """
    try:
        _, _, free = shutil.disk_usage(work_dir)
        return free >= min_bytes
    except Exception:
        return True

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

import subprocess

def _pdf_page_count_via_pdfinfo(pdf_path: str) -> int:
    """
    Fallback using Poppler's pdfinfo (installed via poppler-utils).
    """
    try:
        out = subprocess.check_output(["pdfinfo", pdf_path], stderr=subprocess.DEVNULL)
        for line in out.decode("utf-8", "ignore").splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return 0

def pdf_page_count(pdf_path: str) -> int:
    """
    Return total number of pages in a PDF.
    Tries PyMuPDF first, then pdfinfo. Raises if both fail.
    """
    # Try PyMuPDF (preferred)
    try:
        import fitz  # type: ignore
        with fitz.open(pdf_path) as doc:
            n = int(doc.page_count)
        if n > 0:
            return n
    except Exception:
        # fall through to pdfinfo
        pass
    n = _pdf_page_count_via_pdfinfo(pdf_path)
    if n <= 0:
        raise RuntimeError("could not determine PDF page count")
    return n

def pdf_pages(pdf_path: str) -> int:
    """
    Back-compat alias: some callers expect pdf_pages() to return an int count.
    """
    return pdf_page_count(pdf_path)

def pdf_page_range(total_pages: int):
    """
    1-based page range helper for callers that iterate pages in human terms.
    """
    total = int(max(0, total_pages))
    return range(1, total + 1)

def _clamp_page_index_for_fitz(page_index_1based: int, total_pages: int) -> int:
    """
    Convert a 1-based page index to 0-based for fitz, clamped to [0..total-1].
    Tolerates accidental 0-based input by bumping 0 -> 1.
    """
    if total_pages <= 0:
        return 0
    p = int(page_index_1based)
    if p <= 0:
        p = 1
    if p > total_pages:
        p = total_pages
    return p - 1  # fitz is 0-based

def extract_text_layer(pdf_path: str, page_index: int) -> str:
    """
    Extract *native* text layer for a single page.
    - Accepts page_index as 1-based (tolerates 0-based; clamps safely).
    - Uses PyMuPDF; if it fails, returns "" (callers can escalate to OCR).
    """
    try:
        import fitz  # type: ignore
    except Exception:
        return ""
    try:
        with fitz.open(pdf_path) as doc:
            total = int(doc.page_count)
            idx0 = _clamp_page_index_for_fitz(page_index, total)
            page = doc.load_page(idx0)
            # 'text' gives reading order; 'blocks'/'rawdict' are noisier here
            return page.get_text("text") or ""
    except Exception:
        return ""

def sample_page_indices(total_pages: int, target: int = 5):
    """
    Evenly sample up to 'target' page indices across the document, 1-based.
    Guarantees unique, sorted indices within [1..total_pages].
    """
    n = int(max(0, total_pages))
    t = int(max(1, target))
    if n <= t:
        return list(range(1, n + 1))
    # Even spacing (1-based)
    step = n / float(t + 1)
    picks = sorted({max(1, min(n, int(round(step * i)))) for i in range(1, t + 1)})
    # Ensure we got exactly t unique indices; if not, pad deterministically
    while len(picks) < t:
        for j in range(1, n + 1):
            if j not in picks:
                picks.append(j)
                if len(picks) == t:
                    break
    return sorted(picks)

# ---------- OCR helper ----------

def ocr_image(img, lang: str = "eng", psm: int = 6, oem: int = 1) -> str:
    """
    OCR a Pillow image object or a path-like to an image file.
    Tries pytesseract first; falls back to tesseract CLI. Returns text or "".
    """
    # Try pytesseract first (fastest when available)
    try:
        import pytesseract  # type: ignore
        # Accept PIL.Image.Image directly, otherwise let pytesseract handle the path
        return pytesseract.image_to_string(
            img, lang=lang, config=f"--oem {oem} --psm {psm}"
        )
    except Exception:
        pass

    # Fallback to CLI: ensure we have a path; if a PIL image, write a temp PNG
    import subprocess
    from tempfile import NamedTemporaryFile
    try:
        from PIL import Image  # type: ignore
    except Exception:
        Image = None  # type: ignore

    def _tess_stdout(image_path: str) -> str:
        try:
            out = subprocess.check_output(
                [
                    "tesseract",
                    image_path,
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

    # If it's a PIL image, dump to temp file and OCR
    if Image is not None and hasattr(Image, "Image") and isinstance(img, Image.Image):
        try:
            with NamedTemporaryFile(suffix=".png", delete=True) as tf:
                img.save(tf.name, "PNG")
                return _tess_stdout(tf.name)
        except Exception:
            return ""

    # Otherwise, assume it's a path-like
    try:
        return _tess_stdout(str(img))
    except Exception:
        return ""
