Here’s an updated **README.md** you can paste in, with the GitHub URL added and the DOCX section clarified (full-text extraction without LibreOffice):

```markdown
# Document Extractor (Docker)

A lightweight, headless pipeline that converts mixed document batches into plain text and structured outputs. Designed for UnRAID-style deployments with predictable permissions and a **single `/data` mount**.

**Repository:** https://github.com/strahd-zarovich/document-extractor.git

- **OCR:** English only (`eng`)
- **No WebUI:** operate via folders + logs
- **DOCX:** full-text extraction (body, tables, headers/footers, footnotes/endnotes, comments) — no LibreOffice required
- **Excel (`.xls/.xlsx`)**: routed to **Mandatory Review** (not auto-processed)
- **Delete-after-success:** processed source files are removed; no `.processed.list` needed

---

## How it works

### Folder layout (single `/data` mount)

```

/data/
config/            # runtime config the container uses (copied on first start)
input/             # you place runs here; each subfolder = one run
2025-09-01\_batch/
file1.pdf
file2.docx
output/            # results per run
2025-09-01\_batch/
text/…               # extracted text artifacts
Mandatory Review/…   # files that need manual handling (e.g., .xlsx)
logs/              # (optional) if you configure file logging

````

**Runs:** Each top-level subfolder under `/data/input` is treated as a **run**. The container loops every `INPUT_CHECK_INTERVAL` seconds, finds run folders, and processes them sequentially. Output is mirrored under `/data/output/<RUN_NAME>`.

### Pipeline (per file)

- **PDF (`.pdf`)**
  - Try to extract existing text (`pdftotext -layout`).
  - If no/low text, OCR at sensible DPI.
- **Word**
  - **`.docx`** → Python-based full-text extraction (paragraphs, tables, headers/footers, foot/endnotes, comments).
  - **`.doc`** → Not auto-processed (no LibreOffice); routed to **Mandatory Review**.
- **Text (`.txt`)**
  - Copied/normalized into structured outputs.
- **Excel (`.xls`, `.xlsx`)**
  - **Not** auto-processed. Sent to **`Mandatory Review/`** in the run’s output.

> Any file that fails quality checks is routed to **Mandatory Review** with a reason stamped in `review_manifest.csv`.

### Delete-after-success

When a file’s extraction meets the quality threshold (e.g., minimum non-whitespace chars), the original is **deleted** from `/data/input/<RUN_NAME>` and empty folders are pruned. Failed/unsupported items are preserved under `output/<RUN_NAME>/Mandatory Review`.

---

## Requirements & dependencies

- Base: Debian (slim)
- Installed tools (minimal set):
  - `tesseract-ocr`, `tesseract-ocr-eng` (English OCR)
  - `poppler-utils` (for `pdftotext` / `pdftoppm`)
  - `python3`, `python3-pip`
  - common utilities: `bash`, `file`, `curl`, `inotify-tools` (optional), `unzip`, `gosu`, fonts

> LibreOffice is **not required**. If you later want legacy `.doc/.ppt/.odt` conversion, you can add `libreoffice` and update the docs accordingly.

---

## Configuration

A default config is shipped **inside** the image at `/app/defaults/config.conf`. On first start, it’s copied to `/data/config/config.conf`. Edit the **runtime** file.

**Defaults (excerpt):**
```bash
# Paths
INPUT_DIR="/data/input"
OUTPUT_DIR="/data/output"
LOG_DIR="/data/logs"
WORK_DIR="/tmp/work"

# Logging & polling
LOG_LEVEL="DEBUG"           # switch to INFO after tuning
INPUT_CHECK_INTERVAL=15     # seconds; per-run scan interval

# UnRAID-friendly ownership
PUID=99     # nobody
PGID=100    # users
UMASK=002   # files 0664, dirs 0775

# Large PDF handling
BIGPDF_SIZE_LIMIT_MB=100
BIGPDF_PAGE_LIMIT=500

# Rerun behavior
REPLACE_ON_RERUN=true
````

Environment variables (`PUID`, `PGID`, `TZ`, etc.) can override these in Compose.

---

## Build

```bash
docker build -t document-extractor:latest .
```

> Ensure the Dockerfile installs at least: `tesseract-ocr`, `tesseract-ocr-eng`, `poppler-utils`, `python3`, `python3-pip`.

---

## Run (Compose)

Use a **single** `/data` bind-mount. Healthcheck points to the in-container script path.

```yaml
version: "3.8"

services:
  document-extractor:
    image: document-extractor:latest
    container_name: document-extractor
    user: "99:100"                  # UnRAID-friendly
    restart: unless-stopped

    volumes:
      - /mnt/user/appdata/document-extractor/data:/data

    environment:
      - PUID=99
      - PGID=100
      - TZ=America/New_York

    healthcheck:
      test: ["CMD-SHELL", "/app/scripts/healthcheck.sh"]
      interval: 2m
      timeout: 10s
      retries: 3
      start_period: 30s

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Healthcheck script (update if needed)

```bash
#!/bin/bash
set -euo pipefail

OUT_DIR="${OUTPUT_DIR:-/data/output}"
mkdir -p "$OUT_DIR" || exit 1

TEST_FILE="${OUT_DIR}/.healthcheck"
echo "ok" > "$TEST_FILE" 2>/dev/null || exit 1
rm -f "$TEST_FILE" || true
exit 0
```

---

## Usage

1. Create a run folder and add files:

```
/mnt/user/appdata/document-extractor/data/input/2025-09-01_batch/
  contract.pdf
  letter.docx
  sheet.xlsx      # goes to Mandatory Review
```

2. Start the container (or it will pick up the new run on its next interval).

3. Results appear under:

```
/mnt/user/appdata/document-extractor/data/output/2025-09-01_batch/
  text/…                  # extracted artifacts
  Mandatory Review/…      # unsupported/failed items (e.g., .xlsx, .doc)
  review_manifest.csv     # reasons/notes for manual items
```

4. Source files that passed extraction are **deleted** from `/data/input/<RUN_NAME>` and empty dirs are cleaned up.

---

## Logs

Logs are emitted to container stdout/stderr:

```bash
docker logs -f document-extractor
```

Optionally direct logs to files by mapping `/data/logs` and enabling file logging in scripts.

---

## Notes & known behaviors

* **DOCX:** full-text extraction without LibreOffice.
* **Legacy .doc / Excel:** routed to **Mandatory Review** by design.
* **English-only OCR:** `eng` is used; add other Tesseract packs only if you expand scope.
* **No WebUI:** control via folders and container logs.
* **Reruns:** If `REPLACE_ON_RERUN=true`, a run reprocessed with the same name will overwrite its output folder.

---

## Troubleshooting

* **Nothing happens:** Verify your run folder is directly under `/data/input` (not nested deeper).
* **Healthcheck fails:** Ensure the script path and `/data/output` are correct and writable.
* **Container exits early:** Check `docker logs`. Failures go to **Mandatory Review**; processing continues.
* **Permissions:** Confirm `PUID/PGID` match your host (UnRAID default `99:100`).

```

Want me to also prep a quick `.dockerignore` snippet to keep your image lean?
```
