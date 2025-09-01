# TODO

- [ ] Auto-delete `.wav` files anywhere under `/data/input` (case-insensitive); log `INFO` and remove immediately (do not send to Mandatory Review).
- [ ] Purge all legacy `process_file.sh` references (and any watcher-era stubs) from scripts.
- [ ] Strip all `.bak` files before making a clean release build.
- [ ] Dockerfile: confirm minimal deps only (tesseract-ocr + eng, poppler-utils, python3); remove LibreOffice and any unused packages.
- [ ] Docs: add a note that `.wav` files are auto-deleted (unsupported) and a short “Unsupported types” table in Troubleshooting.
- [ ] Tests: create a tiny test corpus (`docx`, `pdf` w/ and w/o text layer, `png/jpg`, `txt`, `xlsx`, `.wav`) and verify expected routing (Excel → Mandatory Review, `.wav` → deleted).
