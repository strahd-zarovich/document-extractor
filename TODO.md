Here’s an updated `TODO.md` in the same format, reflecting what’s done and what’s next:

```markdown
# TODO

## Image slimming
- [ ] Remove heavy packages (LO already on list): **libreoffice**, **ocrmypdf**, **unoconv**, **docx2txt**, **python3-pdfminer**, **jq**.
- [ ] Remove optional tools unless actually used: **mupdf-tools**, **imagemagick**, **ghostscript**, **libimage-exiftool-perl**.
- [ ] Switch Dockerfile to a minimal deps block (bash, python3, python3-pip, **tesseract-ocr**, **tesseract-ocr-eng**, **poppler-utils**, plus core utils: file, curl, inotify-tools, unzip, gnupg, gosu, fonts-dejavu, fonts-liberation2).
- [ ] Add a `.dockerignore` to prevent bloat (`/data`, `logs/`, `**/*.zip`, `**/*.pdf`, `**/*.docx`, `**/*.xlsx`, `**/*.tif`, `**/*.tiff`, `.git`, etc.).
- [ ] (Optional) Strip docs/locales/icons to shrink: remove `/usr/share/doc/*`, `/usr/share/man/*`, `/usr/share/locale/*`, `/usr/share/icons/*`, `/usr/share/bash-completion/*`.
- [ ] Verify no scripts call removed tools:
      `grep -R -nE 'soffice|unoconv|ocrmypdf|mutool|mudraw|convert|mogrify|exiftool|pdfminer|jq' scripts/`
- [ ] Rebuild and check size: `docker images` and `docker history`.
- [ ] Prune old layers/images: `docker image prune -f && docker builder prune -f`.

## Pipeline & cleanup
- [x] Per-run `run.log` mirrored into `OUTPUT_DIR/<RUN_NAME>/run.log` (added in `process_run.sh` + `common.sh`).
- [ ] Auto-delete `.wav` files on sight (case-insensitive) under `/data/input`; log `INFO` then remove (do **not** move to Mandatory Review).
- [ ] Ensure `move_to_manual.sh` **removes the input original** after routing (prevents re-queues).
- [ ] Add `trap 'rm -rf "$TMP_PATH"' EXIT` right after creating `"$TMP_PATH"` in `process_run.sh` (clean temp on early exit).
- [ ] Remove any `mkdir /tmp` calls (create only `${WORK_DIR:-/tmp/work}` with `mkdir -p`).
- [ ] Purge all legacy `process_file.sh` references (and any watcher-era stubs) from scripts.
- [ ] Strip all `.bak` files before creating a clean release build.
- [ ] Remove empty run folders after success:
      `find "$RUN_PATH" -type d -empty -delete 2>/dev/null || true && rmdir "$RUN_PATH" 2>/dev/null || true`.

## Docs & tests
- [ ] README: note that `.wav` files are auto-deleted and add an “Unsupported types” table (Excel `.xls/.xlsx` & legacy `.doc` → Mandatory Review; `.wav` → deleted).
- [ ] README: confirm **CSV-only outputs** (no `.txt` artifacts).
- [ ] Tests: small corpus (`docx`, `pdf` with/without text layer, `png/jpg`, `txt`, `xlsx`, `.wav`) to verify routing (Excel/`.doc` → Mandatory Review; `.wav` → deleted; CSV populated; no `.txt` artifacts).
```
