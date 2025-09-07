#!/usr/bin/env python3
"""
pass_doc.py — DOC/DOCX extraction with reliability + image OCR fallback for DOCX.

Usage:
  pass_doc.py <path> <csv_out> <json_out> <out_dir>
Exit codes:
  0 = accepted (CSV rows written)
  1 = weak after all attempts (caller may route to Manual Review)
  2 = usage
 10 = hard skip (missing tools, unreadable), caller decides

Env cutoffs (tweakable):
  DOCX_CUTOFF         default 0.60  (native text acceptance)
  DOC_IMG_OCR_CUTOFF  default 0.50  (per-image OCR acceptance)
  DOC_IMG_MAX         default 12    (cap images OCR’d)
"""

from __future__ import annotations
import os, sys, io, zipfile, subprocess
from typing import List, Tuple
from PIL import Image
from common import get_logger, CsvWriter, score_reliability

# Try python-docx (apt: python3-docx or pip: python-docx)
try:
    import docx  # type: ignore
except Exception:  # docx may be missing; we handle gracefully for .doc path
    docx = None

DOCX_CUTOFF        = float(os.getenv("DOCX_CUTOFF", "0.60"))
DOC_IMG_OCR_CUTOFF = float(os.getenv("DOC_IMG_OCR_CUTOFF", "0.50"))
DOC_IMG_MAX        = int(os.getenv("DOC_IMG_MAX", "12"))

def _read_all(fpath: str) -> str:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()

def _docx_extract_text(path: str) -> str:
    if docx is None:
        return ""
    d = docx.Document(path)
    parts: List[str] = []

    # body paragraphs
    for p in d.paragraphs:
        if p.text: parts.append(p.text)

    # tables
    for table in d.tables:
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            if any(cells):
                parts.append("\t".join(cells))

    # headers/footers (all sections)
    try:
        for sec in d.sections:
            for p in sec.header.paragraphs:
                if p.text: parts.append(p.text)
            for p in sec.footer.paragraphs:
                if p.text: parts.append(p.text)
    except Exception:
        pass

    return "\n".join(parts)

def _docx_extract_images(path: str) -> List[Image.Image]:
    imgs: List[Image.Image] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [n for n in zf.namelist() if n.startswith("word/media/")]
            for n in names[:DOC_IMG_MAX]:
                try:
                    data = zf.read(n)
                    img = Image.open(io.BytesIO(data)).convert("L")
                    # small upsample if very tiny
                    if min(img.size) < 600:
                        w, h = img.size
                        img = img.resize((w*2, h*2))
                    imgs.append(img)
                except Exception:
                    continue
    except Exception:
        pass
    return imgs

def _run_cmd(cmd: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        out = p.stdout.decode("utf-8", "ignore")
        return p.returncode, out
    except Exception as e:
        return 127, f"{e}"

def _doc_antiword(path: str) -> str:
    rc, out = _run_cmd(["antiword", "-m", "UTF-8.txt", path])
    if rc == 0 and out.strip():
        return out
    # fallback: catdoc if available
    rc2, out2 = _run_cmd(["bash", "-lc", f"command -v catdoc >/dev/null 2>&1 && catdoc -dutf-8 -w {sh_quote(path)} || exit 127"])
    if rc2 == 0 and out2.strip():
        return out2
    return ""

def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

def _ocr_image(img: Image.Image) -> str:
    try:
        import pytesseract
    except Exception:
        return ""
    try:
        return pytesseract.image_to_string(img, lang="eng", config="--oem 1 --psm 6")
    except Exception:
        return ""

def main(path: str, csv_out: str, _json_out: str, _out_dir: str) -> int:
    log = get_logger(os.getenv("RUN_LOG"))
    base = os.path.basename(path)
    ext = os.path.splitext(base)[1].lower()

    # prepare CSV
    cw = CsvWriter(csv_out, logger=log)

    if ext == ".docx":
        if docx is None:
            log.warn(f"python-docx not available; cannot parse DOCX natively: {base}")
            imgs = _docx_extract_images(path)  # still try OCR on images via zip
            accepted = 0
            for idx, im in enumerate(imgs, start=1):
                txt = _ocr_image(im)
                rel = score_reliability(txt)
                if rel >= DOC_IMG_OCR_CUTOFF and txt.strip():
                    cw.row(base, f"img{idx}", txt, "docx_img_ocr", True, reliability=rel)
                    accepted += 1
            if accepted > 0:
                log.info(f"DOCX accepted via image OCR: pages={accepted}")
                return 0
            return 1

        # Native text
        text = _docx_extract_text(path)
        rel = score_reliability(text)
        log.info(f"DOCX native summary: chars={len(text)} rel={rel:.2f}")
        if rel >= DOCX_CUTOFF and text.strip():
            cw.row(base, "", text, "docx_native", False, reliability=rel)
            log.info(f"DOCX native accepted: {base}")
            return 0

        # Fallback: OCR embedded images
        imgs = _docx_extract_images(path)
        accepted = 0
        for idx, im in enumerate(imgs, start=1):
            txt = _ocr_image(im)
            reli = score_reliability(txt)
            if reli >= DOC_IMG_OCR_CUTOFF and txt.strip():
                cw.row(base, f"img{idx}", txt, "docx_img_ocr", True, reliability=reli)
                accepted += 1

        if accepted > 0:
            log.info(f"DOCX accepted via image OCR: images_passed={accepted}")
            return 0

        log.warn(f"DOCX below cutoff after native+OCR: {base}")
        return 1

    elif ext == ".doc":
        text = _doc_antiword(path)
        rel = score_reliability(text)
        log.info(f"DOC (antiword) summary: chars={len(text)} rel={rel:.2f}")
        if rel >= float(os.getenv("DOC_CUTOFF", "0.55")) and text.strip():
            cw.row(base, "", text, "doc_native", False, reliability=rel)
            log.info(f"DOC accepted via antiword: {base}")
            return 0
        if text.strip():
            # weak text, still write a row so you see something (optional); comment out if not wanted
            cw.row(base, "", text, "doc_native_weak", False, reliability=rel)
        log.warn(f"DOC below cutoff after antiword (and catdoc fallback if present): {base}")
        return 1

    else:
        log.warn(f"pass_doc.py called on unsupported extension: {base}")
        return 10

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
