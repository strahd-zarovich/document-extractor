# TODO

## Image slimming
- [ ] Remove heavy packages (LO already planned): **libreoffice**, **ocrmypdf**, **unoconv**, **docx2txt**, **python3-pdfminer**, **jq**.
- [ ] Drop optional tools unless used: **mupdf-tools**, **imagemagick**, **ghostscript**, **libimage-exiftool-perl**.
- [ ] Use minimal deps block (bash, python3, python3-pip, **tesseract-ocr**, **tesseract-ocr-eng**, **poppler-utils**, **python3-docx**, core utils).
- [ ] Add `.dockerignore` (exclude `/data`, `logs/`, `*.zip`, `*.pdf`, `*.docx`, `*.xlsx`, `.git`, etc.).
- [ ] (Optional) Strip docs/locales/icons to shrink image.
- [ ] Verify no scripts call removed tools; rebuild and prune old layers.

## Pipeline & cleanup
- [ ] Auto-delete `.wav` files on sight (case-insensitive) under `/data/input`; log `INFO` and remove (do not send to Mandatory Review).
- [ ] Purge all legacy `process_file.sh` references (watcher-era stubs).
- [ ] Strip all `.bak` files before a clean release build.

## Temp workspace hardening (NEW)
- [ ] In `process_run.sh`, add `trap 'rm -rf "$TMP_PATH"' EXIT` after creating `$TMP_PATH` so it’s always cleaned.
- [ ] In `entrypoint.sh`, keep the startup wipe of `${WORK_DIR:-/tmp/work}`; add optional pruning of stale dirs:
      `find "${WORK_DIR:-/tmp/work}" -mindepth 1 -maxdepth 1 -type d -mmin +120 -exec rm -rf {} + 2>/dev/null || true`
- [ ] Ensure all per-pass scripts already `trap` their temp files/dirs (PDF/DOCX passes verified).

## Docs & tests
- [ ] README: note that `.wav` files are auto-deleted; add “Unsupported types” table.
- [ ] Tests: small corpus (`docx`, `pdf` with/without text layer, `png/jpg`, `txt`, `xlsx`, `.wav`) to verify routing/behavior.
