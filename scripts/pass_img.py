#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image OCR pass: TIFF/PNG/JPG, including multi-frame TIFF.
Writes 6-column CSV rows; English OCR; per-image or per-frame rows.
Args:
  1: path to image
  2: path to CSV for this run
  3: path to run.log
Env:
  LOG_LEVEL (INFO/DEBUG), optional
"""
import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import common
from PIL import Image, UnidentifiedImageError


def _run_ocr_variants(img, logger, basename: str, frame_index: int) -> tuple[str, float]:
    """
    Multi-pass OCR for a single frame:
      - Variant A: grayscale
      - Variant B: grayscale + simple threshold
    Returns (best_text, best_reliability).
    """
    variants = []

    # Variant A: plain grayscale
    try:
        gray = img.convert("L")
        variants.append(("gray", gray, 6, 1))
    except Exception as e:
        if logger:
            logger.debug(f"{basename} frame={frame_index}: grayscale convert failed: {e}")

    # Variant B: grayscale + simple threshold
    try:
        if variants:
            base = variants[0][1]
        else:
            base = img.convert("L")
        # simple binary threshold at mid-level
        th = base.point(lambda v: 0 if v < 128 else 255)
        variants.append(("gray_thresh", th, 6, 1))
    except Exception as e:
        if logger:
            logger.debug(f"{basename} frame={frame_index}: threshold convert failed: {e}")

    best_text = ""
    best_rel = 0.0

    for label, variant_img, psm, oem in variants:
        try:
            text = common.ocr_image(variant_img, lang="eng", psm=psm, oem=oem) or ""
            rel = common.score_reliability(text)
            if logger:
                logger.debug(
                    f"{basename} frame={frame_index} variant={label} "
                    f"psm={psm} oem={oem} reliability={rel:.2f}"
                )
        except Exception as e:
            if logger:
                logger.debug(
                    f"{basename} frame={frame_index} variant={label} OCR error: {e}"
                )
            text, rel = "", 0.0

        if rel > best_rel:
            best_rel = rel
            best_text = text

    # If everything failed, ensure we return something
    return best_text or "", best_rel


def _ocr_frame(img, logger, basename: str, frame_index: int) -> tuple[str, float]:
    """
    Wrapper used by main(): runs multi-pass OCR and returns (text, reliability).
    """
    return _run_ocr_variants(img, logger, basename, frame_index)


def main():
    if len(sys.argv) < 4:
        print("usage: pass_img.py <image_path> <csv_path> <run_log_path>", file=sys.stderr)
        sys.exit(2)

    img_path, csv_path, run_log_path = sys.argv[1], sys.argv[2], sys.argv[3]
    logger = common.get_logger(run_log_path)
    writer = common.CsvWriter(csv_path)
    basename = os.path.basename(img_path)

    try:
        im = Image.open(img_path)
    except UnidentifiedImageError as e:
        logger.error(f"IMG open failed: {basename} :: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"IMG open error: {basename} :: {e}")
        sys.exit(1)

    frames = getattr(im, "n_frames", 1)
    rows_written = 0
    try:
        for idx in range(frames):
            try:
                if frames > 1:
                    im.seek(idx)
                # Use the multi-pass OCR helper
                text, rel = _ocr_frame(im, logger, basename, idx + 1)
            except Exception as e:
                logger.warning(f"IMG OCR error @{idx+1}: {e}")
                text, rel = "", 0.0

            # Always 6 columns; per-frame rows for multi-frame inputs
            page_display = str(idx + 1) if frames > 1 else "-"
            writer.write_row(
                basename,
                page_display,
                text,
                "img_ocr",
                "true",
                f"{rel:.2f}",
            )
            rows_written += 1

        logger.info(f"IMG file accepted: {basename} frames={frames} rows={rows_written}")
        sys.exit(0)
    finally:
        try:
            im.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
