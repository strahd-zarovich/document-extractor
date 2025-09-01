# 📄 Document Extractor – Dockerized Text Processing

## Overview

This container is designed to extract as much text as possible from a wide range of document formats. It uses **multi-pass extraction** with fallback strategies (native text, OCR, multi-engine PDF tools) and organizes results into structured output folders.

Key features:

* Supports **DOC, DOCX, PDF, Images (JPG/PNG/TIFF)**, and more.
* Multi-pass extraction:

  1. DOC/DOCX → text
  2. PDF (native text)
  3. PDF OCR (tesseract)
  4. PDF OCR (mupdf-tools)
* Handles multiple **top-level input folders** at once.
* Moves unprocessable files into a **Mandatory Review Folder**.
* Produces both **CSV and JSON** outputs.
* Automatically cleans up manifests and tmp data on startup.
* Ensures **UnRAID-friendly permissions** (owner 99, group 100).

---

## Folder Structure

When running, the container maintains:

```
/input
   └── MyFolder1/
   └── MyFolder2/
   ...

/output
   └── MyFolder1/
       ├── MyFolder1.csv
       ├── MyFolder1.json
       └── Mandatory Review Folder/
   └── MyFolder2/
       ├── MyFolder2.csv
       ├── MyFolder2.json
       └── Mandatory Review Folder/

/tmp        → temporary working area
/manifests  → manifest lists to track processed files
/app        → scripts + config
```

* **Processed files** are deleted after extraction.
* **Empty folders** under `/input` are cleaned up (but `/input` itself is never deleted).
* **Problematic files** are moved into the *Mandatory Review Folder*.

---

## Configuration

Global config lives in:
`/app/config.conf`

Default variables:

```bash
INPUT_DIR="/input"
OUTPUT_DIR="/output"
TMP_DIR="/tmp"
MANIFEST_DIR="/manifests"

INPUT_CHECK_INTERVAL=15    # seconds between scans
LOG_LEVEL="DEBUG"          # DEBUG, INFO, WARN, ERROR
PDF_OCR_THRESHOLD=50       # pages – above this, large PDFs split into per-page CSVs
```

* **INPUT\_CHECK\_INTERVAL** – how often the watcher scans `/input`.
* **LOG\_LEVEL** – start in DEBUG for development, later switch to INFO.
* **PDF\_OCR\_THRESHOLD** – if a PDF exceeds this many pages, it is split into smaller chunks for easier processing.

---

## Usage

### 1. Build

From inside the repo folder:

```bash
docker build -t document-extractor:latest .
```

### 2. Run

Basic run (UnRAID-friendly):

```bash
docker run -d \
  --name=document-extractor \
  -v /mnt/user/appdata/document-extractor/input:/input \
  -v /mnt/user/appdata/document-extractor/output:/output \
  document-extractor:latest
```

Optional: override config values at runtime:

```bash
-e INPUT_CHECK_INTERVAL=30 \
-e LOG_LEVEL=INFO \
```

---

## Logs

Logs are verbose in `DEBUG` mode:

```bash
docker logs -f document-extractor
```

* During testing: keep `DEBUG` to trace every pass.
* After stable: set `INFO` for lighter logs.

---

## Development Notes

* **Manifests** prevent reprocessing of already completed files. On restart, manifests are cleared so files are rescanned.
* **Permissions** are enforced via `fix_permissions.sh`. Everything is owned by `nobody:users` (`99:100`).
* **Watch Loop** (`watch_input.sh`) never logs the idle `/input` check to prevent log bloat. Only activity (found files, errors, review moves) is logged.
* **Manual Review** – anything unsupported, corrupted, or too ambiguous is moved here automatically.

---

## Roadmap / Enhancements

* Multi-pass OCR tuning (DPI, language packs) can be set inside each pass script.
* Optional: add healthcheck script to validate dependencies.
* Optional: add export compression (`.zip` outputs).

---
# document-extractor
