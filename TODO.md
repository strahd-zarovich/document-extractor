# TODO

## Image slimming
- [ ] Remove heavy packages if present: **libreoffice**, **ocrmypdf**, **unoconv**, **docx2txt**, **python3-pdfminer**, **jq**.
- [ ] Drop optional tools unless actually used: **mupdf-tools**, **imagemagick**, **ghostscript**, **libimage-exiftool-perl**.
- [ ] Use minimal deps in Dockerfile (lean “Option B”): bash, python3, python3-pip, **tesseract-ocr**, **tesseract-ocr-eng**, **poppler-utils**, core utils (file, curl, unzip, gnupg, gosu, fonts-dejavu, fonts-liberation2, inotify-tools).
- [ ] Add `.dockerignore` to prevent bloat (`/data`, `logs/`, `**/*.zip`, `**/*.pdf`, `**/*.docx`, `**/*.xlsx`, `**/*.tif`, `**/*.tiff`, `.git`, etc.).
- [ ] (Optional) Extra trim: remove `/usr/share/doc/*`, `/usr/share/man/*`, `/usr/share/locale/*`, `/usr/share/icons/*`, `/usr/share/bash-completion/*`.
- [ ] **Do not re-add MuPDF**; stay with Poppler + Tesseract.

## Pipeline & cleanup
- [x] **Per-run log** mirrored to `OUTPUT_DIR/<RUN_NAME>/run.log` (start/end banners + messages).
- [x] **CSV-only outputs** (no per-file `.txt` artifacts).
- [x] **Auto-delete `.wav`** files on sight; log `INFO`, delete immediately (no Manual Review).
- [x] **Delete input originals** after successful processing or after routing to Manual Review.
- [x] **Trap for temp cleanup**: `trap 'rm -rf "$TMP_PATH"' EXIT` after creating `"$TMP_PATH"`.
- [x] **No `mkdir /tmp`** calls (only create `${WORK_DIR:-/tmp/work}` with `mkdir -p`).
- [ ] Purge any legacy `process_file.sh` references or watcher-era stubs (if still present).
- [ ] Strip any `.bak` files before making a clean release build.

## CSV schema & consistency
- [ ] **Header alignment:** Update run CSV header to `filename,page,text,method,used_ocr` (rows are already 5 columns).
- [ ] (Optional) Backfill old CSVs’ first line:
      `sed -i '1 s/^filename,page,text$/filename,page,text,method,used_ocr/' /path/to/run/*.csv`
- [ ] Normalize `method` values across passes (use: `docx`, `pdf_text`, `ocr`, `ocr_deep`, `img_ocr`, `doc`).
- [ ] Ensure `used_ocr` is strictly `true|false` (string) across all writers.

## Legacy .doc handling (no LibreOffice)
- [ ] Add **antiword** to Dockerfile (lightweight).
- [ ] Update `pass_doc.sh` to handle `.doc` via **antiword** (CSV-only). If extraction fails/too short → Manual Review.

## OCR robustness (simple, fixed logic; no new env vars)
- [ ] **PDF deep fallback:** keep current flow, then add a fixed second OCR step:
      - Step A (existing): `pdftoppm -r 300 -gray` → `tesseract -l eng --oem 1 --psm 6`; accept if ≥120 chars.
      - Step B (new): only if Step A too short; re-render `-r 400 -gray`, per-page try rotations **0°/90°/270°** with PSM **6 → 3**; accept if ≥80 chars.
      - Record `method=ocr` for Step A, `method=ocr_deep` for Step B; `used_ocr=true`.
- [ ] **DOCX embedded-image OCR fallback:** when DOCX text <120 chars:
      - Extract `word/media/*` images (png/jpg/tif/gif), skip EMF/WMF.
      - OCR each image with the same **Step B** ladder; one CSV row per image (`page` = image index), `method=img_ocr`, `used_ocr=true`.
      - Hard cap at **25** images per DOCX.

## Standalone image OCR (optional)
- [ ] Decide whether to OCR `tif/tiff/png/jpg/jpeg` automatically vs keep in Manual Review.
      - If enabled, add a small `pass_img.sh` using the same **Step B** ladder; CSV-only; `method=img_ocr`.

## Docs & tests
- [ ] README: document the **5-column CSV schema** and meanings:
      - `filename`: full input path at processing time
      - `page`: 1-based page/image index
      - `text`: extracted text (newlines as `\n`, quotes CSV-escaped)
      - `method`: `docx | pdf_text | ocr | ocr_deep | img_ocr | doc`
      - `used_ocr`: `true|false`
- [ ] README: call out behaviors (Excel `.xls/.xlsx` → Manual Review; `.wav` → deleted; `.doc` → antiword if enabled).
- [ ] Tests: small corpus (`docx` with/without embedded images, `pdf` with/without text layer, `png/jpg`, `tif`, `txt`, `xlsx`, `.doc`, `.wav`) to verify routing and CSV schema (5 columns, no `.txt` artifacts).
