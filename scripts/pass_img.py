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

def _ocr_frame(img) -> tuple[str, float]:
    text = common.ocr_image(img, lang="eng", psm=6, oem=1) or ""
    rel = common.score_reliability(text)
    return text, rel

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
                # Convert to grayscale to normalize
                g = im.convert("L")
                text, rel = _ocr_frame(g)
            except Exception as e:
                logger.warning(f"IMG OCR error @{idx+1}: {e}")
                text, rel = "", 0.0

            # Always 6 columns; per-frame rows for multi-frame inputs
            page_display = str(idx + 1) if frames > 1 else "-"
            writer.write_row(basename, page_display, text, "img_ocr", "true", f"{rel:.2f}")
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
