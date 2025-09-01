# TODO

## Image slimming
- [ ] Remove heavy packages (LO already on list): **libreoffice**, **ocrmypdf**, **unoconv**, **docx2txt**, **python3-pdfminer**, **jq**.
- [ ] Remove optional tools unless actually used: **mupdf-tools**, **imagemagick**, **ghostscript**, **libimage-exiftool-perl**.
- [ ] Switch Dockerfile to a minimal deps block (bash, python3, python3-pip, **tesseract-ocr**, **tesseract-ocr-eng**, **poppler-utils**, **python3-docx**, plus core utils: file, curl, inotify-tools, unzip, gnupg, gosu, fonts-dejavu, fonts-liberation2).
- [ ] Add a `.dockerignore` to prevent bloat (`/data`, `logs/`, `**/*.zip`, `**/*.pdf`, `**/*.docx`, `**/*.xlsx`, `.git`, etc.).
- [ ] (Optional) Strip docs/locales/icons to shrink: remove `/usr/share/doc/*`, `/usr/share/man/*`, `/usr/share/locale/*`, `/usr/share/icons/*`, `/usr/share/bash-completion/*`.
- [ ] Verify no scripts call removed tools:
      `grep -R -nE 'soffice|unoconv|ocrmypdf|mutool|mudraw|convert|mogrify|exiftool|pdfminer|jq' scripts/`
- [ ] Rebuild and check size: `docker images` and `docker history`.
- [ ] Prune old layers/images: `docker image prune -f && docker builder prune -f`.

## Pipeline & cleanup
- [ ] Auto-delete `.wav` files on sight (case-insensitive) under `/data/input`; log `INFO` then remove (do not move to Mandatory Review).
- [ ] Purge all legacy `process_file.sh` references (and any watcher-era stubs) from scripts.
- [ ] Strip all `.bak` files before creating a clean release build.

## Docs & tests
- [ ] README: note that `.wav` files are auto-deleted and add an “Unsupported types” table.
- [ ] Tests: small corpus (`docx`, `pdf` with/without text layer, `png/jpg`, `txt`, `xlsx`, `.wav`) to verify routing (Excel → Mandatory Review; `.wav` → deleted).
