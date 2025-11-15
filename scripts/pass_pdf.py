#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF orchestrator: TXT -> OCR-A -> OCR-B with per-doc / per-page switching.
Args:
  1: path to PDF
  2: path to CSV for this run
  3: path to run.log
Env (optional):
  PASS_TXT_CUTOFF (float, default 0.80)
  PASS_OCR_A_CUTOFF (float, default 0.70)
  PASS_OCR_B_CUTOFF (float, default 0.60)
  BIGPDF_SIZE_LIMIT_MB (int, default 50)
  BIGPDF_PAGE_LIMIT (int, default 500)
  WORK_DIR (path, default /tmp/work)
  LOG_LEVEL (INFO/DEBUG, default INFO)
Notes:
  - Writes rows to CSV on accept; exits 0.
  - Returns 1 on failure so process_run.py can quarantine.
"""
import os, sys, shutil, math

# Make sure we can import sibling modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import common  # project shared utils
import pass_pdf_txt  # local module (below)
import output_writer
# OCR modules will come in next pages; we 'import' but guard missing ones for now.
try:
    import pass_pdf_ocr_a
except Exception:
    pass
try:
    import pass_pdf_ocr_b
except Exception:
    pass

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def _safe_float(value, default: float = 0.0) -> float:
    """Convert a value to float safely, returning default on any failure."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def _coerce_text(value) -> str:
    """Coerce any payload 'text' field to a safe string."""
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""

def _get_free_mb(path: str) -> int:
    try:
        usage = shutil.disk_usage(path)
        return int(usage.free / (1024 * 1024))
    except Exception:
        return -1  # unknown

def _file_size_mb(path: str) -> int:
    try:
        return int(math.ceil(os.path.getsize(path) / (1024 * 1024)))
    except Exception:
        return 0

def main():
    if len(sys.argv) < 4:
        print("usage: pass_pdf.py <pdf_path> <csv_path> <run_log_path>", file=sys.stderr)
        sys.exit(2)

    pdf_path, csv_path, run_log_path = sys.argv[1], sys.argv[2], sys.argv[3]

    # thresholds and config
    PASS_TXT_CUTOFF = _env_float("PASS_TXT_CUTOFF", 0.80)
    PASS_OCR_A_CUTOFF = _env_float("PASS_OCR_A_CUTOFF", 0.70)
    PASS_OCR_B_CUTOFF = _env_float("PASS_OCR_B_CUTOFF", 0.60)
    BIGPDF_SIZE_LIMIT_MB = _env_int("BIGPDF_SIZE_LIMIT_MB", 50)
    BIGPDF_PAGE_LIMIT = _env_int("BIGPDF_PAGE_LIMIT", 500)
    WORK_DIR = os.getenv("WORK_DIR", "/tmp/work")

    logger = common.get_logger(run_log_path)

    # Basic file metadata
    try:
        total_pages = common.pdf_page_count(pdf_path)
    except Exception as e:
        logger.error(f"PDF open failed: {pdf_path} :: {e}")
        sys.exit(1)

    size_mb = _file_size_mb(pdf_path)
    mode = "per-page" if (size_mb >= BIGPDF_SIZE_LIMIT_MB or total_pages >= BIGPDF_PAGE_LIMIT) else "per-doc"
    logger.info(f"PDF start: {os.path.basename(pdf_path)} pages={total_pages} size_mb={size_mb} mode={mode}")

    # ===== Pass 1: TXT =====
    logger.info(f"TXT begin: {os.path.basename(pdf_path)}")
    try:
        txt_ok, txt_payload = pass_pdf_txt.run(pdf_path, mode=mode, cutoff=PASS_TXT_CUTOFF, logger=logger)
    except Exception as e:
        logger.warning(f"TXT error: {e}")
        txt_ok, txt_payload = False, None

    if txt_ok and txt_payload:
        # Build pages list and a single doc-level score for the TXT pass
        if mode == "per-doc":
            # Treat the entire document as a single "page 1"
            pages = [(1, _coerce_text(txt_payload.get("text")))]
            # Prefer payload['reliability'] if present
            score = _safe_float(txt_payload.get("reliability"), 0.0)
            logger.info(
                f"TXT accept (per-doc): pages={total_pages} median={score:.2f}"
            )
        else:
            # per-page: keep each page as its own page number
            page_rows = txt_payload.get("pages") or []
            pages = [
                (int(row.get("page", 0)), _coerce_text(row.get("text"))) for row in page_rows]

            # Try to find a doc-level reliability, else fall back to max per-page reliability
            if "reliability" in txt_payload:
                score = _safe_float(txt_payload.get("reliability"), 0.0)
            else:
                score = max(
                    (_safe_float(row.get("reliability"), 0.0) for row in page_rows),
                    default=0.0,
                )
            logger.info(
                f"TXT accept (per-page): pages={len(pages)} best_rel={score:.2f}"
            )

        # Use centralized writer to create the .txt and append a single index row
        output_writer.write_result(
            csv_path=csv_path,
            original_file=os.path.abspath(pdf_path),
            pages=pages,
            pass_used="pdf_text",
            score=score,
            status="OK",
            used_ocr=False,
            logger=logger,
        )
        sys.exit(0)
    else:
        logger.info(f"TXT escalate: cutoff={PASS_TXT_CUTOFF}")
    
    # v0.1.4: switch to per-page once OCR is required
    if mode == "per-doc":
        mode = "per-page"
        logger.info("Switching to per-page because OCR is required.")

    # Before OCR: low-workdir-space guard
    free_mb = _get_free_mb(WORK_DIR)
    if free_mb >= 0 and free_mb < 1024:
        logger.error(f"LOW_DISK: workdir_free_mb={free_mb} threshold=1024 -- failing file before OCR")
        # Non-zero so orchestrator can move to Mandatory Review
        sys.exit(1)

    # ===== Pass 2: OCR-A =====
    logger.info(f"OCR A begin: {os.path.basename(pdf_path)}")
    try:
        ocr_a_ok, ocr_a_payload = pass_pdf_ocr_a.run(pdf_path, mode=mode, cutoff=PASS_OCR_A_CUTOFF, logger=logger)
    except Exception as e:
        logger.warning(f"OCR A error: {e}")
        ocr_a_ok, ocr_a_payload = False, None

    if ocr_a_ok and ocr_a_payload:
        # Build pages list and a single doc-level score for OCR-A
        if mode == "per-doc":
            pages = [(1, _coerce_text(ocr_a_payload.get("text")))]
            score = _safe_float(ocr_a_payload.get("reliability"), 0.0)
            logger.info(f"OCR A accept (per-doc): median={score:.2f}")
        else:
            page_rows = ocr_a_payload.get("pages") or []
            pages = [(int(row.get("page", 0)), _coerce_text(row.get("text"))) for row in page_rows]

            if "reliability" in ocr_a_payload:
                score = _safe_float(ocr_a_payload.get("reliability"), 0.0)
            else:
                score = max(
                    (_safe_float(row.get("reliability"), 0.0) for row in page_rows),
                    default=0.0,
                )
            logger.info(f"OCR A accept (per-page): pages={len(pages)} best_rel={score:.2f}")

        # Use centralized writer to create the .txt and append a single index row
        output_writer.write_result(
            csv_path=csv_path,
            original_file=os.path.abspath(pdf_path),
            pages=pages,
            pass_used="pdf_ocr_a",
            score=score,
            status="OK",
            used_ocr=True,
            logger=logger,
        )
        sys.exit(0)
    else:
        logger.info(f"OCR A escalate: cutoff={PASS_OCR_A_CUTOFF}")

    # ===== Pass 3: OCR-B =====
    # NOTE: Per your spec, drop the duplicate "begin" inside the pass; log only here.
    logger.info(f"OCR B begin: {os.path.basename(pdf_path)}")
    try:
        ocr_b_ok, ocr_b_payload = pass_pdf_ocr_b.run(pdf_path, mode=mode, cutoff=PASS_OCR_B_CUTOFF, logger=logger)
    except Exception as e:
        logger.warning(f"OCR B error: {e}")
        ocr_b_ok, ocr_b_payload = False, None

    if ocr_b_ok and ocr_b_payload:
        # Build pages list and a single doc-level score for OCR-B
        if mode == "per-doc":
            pages = [(1, _coerce_text(ocr_b_payload.get("text")))]
            score = _safe_float(ocr_b_payload.get("reliability"), 0.0)
            logger.info(f"OCR B accept (per-doc): median={score:.2f}")
        else:
            page_rows = ocr_b_payload.get("pages") or []
            pages = [(int(row.get("page", 0)), _coerce_text(row.get("text"))) for row in page_rows]

            if "reliability" in ocr_b_payload:
                score = _safe_float(ocr_b_payload.get("reliability"), 0.0)
            else:
                score = max(
                    (_safe_float(row.get("reliability"), 0.0) for row in page_rows),
                    default=0.0,
                )
            logger.info(f"OCR B accept (per-page): pages={len(pages)} best_rel={score:.2f}")

        output_writer.write_result(
            csv_path=csv_path,
            original_file=os.path.abspath(pdf_path),
            pages=pages,
            pass_used="pdf_ocr_b",
            score=score,
            status="OK",
            used_ocr=True,
            logger=logger,
        )
        sys.exit(0)

    # All passes failed: no pass produced an acceptable result.
    # Record this in the CSV index but do NOT write any .txt file.
    logger.error(f"PDF failed: {os.path.basename(pdf_path)} -- all passes below cutoff or errored")
    output_writer.write_result(
        csv_path=csv_path,
        original_file=os.path.abspath(pdf_path),
        pages=[],           # empty => output_writer skips creating a text file
        pass_used="pdf_ocr_b",  # last attempted pass
        score=0.0,
        status="ERROR",
        used_ocr=True,
        logger=logger,
    )
    sys.exit(1)

if __name__ == "__main__":
    main()
