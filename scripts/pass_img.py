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
import output_writer
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
    pages = []
    best_rel = 0.0
    has_text = False

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

            # Track per-frame text and reliability
            pages.append((idx + 1, text))
            if text.strip():
                has_text = True
            if rel > best_rel:
                best_rel = rel

        # Decide status based on whether any usable text was found
        if has_text:
            status = "OK"
            # We keep all frames as pages; some may have blank text, which is fine.
            output_writer.write_result(
                csv_path=csv_path,
                original_file=os.path.abspath(img_path),
                pages=pages,
                pass_used="img_ocr",
                score=best_rel,
                status=status,
                used_ocr=True,
                logger=logger,
            )
            logger.info(f"IMG file accepted: {basename} frames={frames} pages={len(pages)} best_rel={best_rel:.2f}")
            sys.exit(0)
        else:
            # No usable text: append CSV row only, but do NOT write any .txt file
            output_writer.write_result(
                csv_path=csv_path,
                original_file=os.path.abspath(img_path),
                pages=[],  # empty => output_writer will skip creating a text file
                pass_used="img_ocr",
                score=best_rel,
                status="ERROR",
                used_ocr=True,
                logger=logger,
            )
            logger.warning(f"IMG had no usable text: {basename} frames={frames}")
            sys.exit(1)
    finally:
        try:
            im.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
