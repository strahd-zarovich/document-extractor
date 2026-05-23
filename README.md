# Document Extractor Docker (0.1.9)

A Docker-based document extraction pipeline designed for large mixed-document collections.

The container recursively processes PDFs, Office documents, text files, and images using a staged extraction pipeline:

1. Native text extraction
2. OCR-A (balanced OCR)
3. OCR-B (aggressive OCR fallback)
4. Mandatory Review quarantine when confidence is too low

The goal is:
- maximize automated extraction,
- preserve forensic traceability,
- minimize silent failures,
- and make debugging easy when extraction fails.

---

# Major Features

## Multi-Pass PDF Processing

PDFs are processed in stages:

1. TXT extraction
2. OCR-A fallback
3. OCR-B fallback
4. Mandatory Review

Each stage uses reliability scoring before acceptance.

---

## Reliability Scoring

Every extraction path generates a reliability score:

- TXT
- OCR-A
- OCR-B
- DOC/DOCX
- Images

Reliability values are written into the CSV output.

---

## One TXT Per Source Document

Each processed document produces:

```text
document.txt
```

with:

- metadata header,
- page separators,
- normalized UTF-8 output.

---

## Embedded Portfolio Extraction

PDF portfolios and embedded attachments are automatically extracted.

Embedded children preserve forensic parent-child lineage.

Example lineage:

```text
Parent.pdf / Embedded.pdf / Child.xlsx
```

Physical filenames are automatically shortened when necessary to avoid:

- Windows path-length issues
- SMB filename issues
- extraction failures from excessively long embedded names

Lineage metadata is preserved inside:

- portfolio_manifest.csv
- review_manifest.csv

Parent portfolio PDFs are moved into:

```text
$WORK_DIR/portfolio_hidden/<run>/
```

to prevent recursive reprocessing.

---

## Mandatory Review System

Files that cannot be safely processed are moved into:

```text
Mandatory Review/
```

with:

- readable logical filenames,
- preserved embedded lineage,
- review_manifest.csv,
- detailed logging.

Review manifests preserve:

- original full generated filenames
- portfolio lineage paths
- normalized review reasons

Random temp names like:

```text
C3XWAM~P
```

are no longer used in 0.1.8+.

---

## Configurable Extension Rules

Behavior is controlled through editable config files:

```text
/data/config/
```

Including:

- delete_extensions.txt
- ignore_files.txt
- manual_review_extensions.txt

---

# Config File Behavior

The container only seeds default config files on first startup.

If a config file already exists inside:

```text
/data/config/
```

it will NOT be overwritten during:

- container rebuilds,
- image updates,
- version upgrades.

This is intentional so user-customized rules survive upgrades.

To receive newer default rules:

1. Manually update the existing config file, OR
2. Delete the config file and restart the container to reseed it from:

```text
/app/defaults/
```

---

# Current File Policies (0.1.9)

## Auto-Delete Extensions

These are treated as noise files and deleted automatically:

```text
.wav
.msg
.pptx
.ptx
```

---

## Manual Review Extensions

These currently route directly to Mandatory Review:

```text
.doc
.xlsx
```

Reason:

- old DOC conversion is unreliable,
- XLSX extraction policy is still under evaluation.

---

## Ignored Internal Files

```text
portfolio_manifest.csv
review_manifest.csv
.processed.list
```

These are ignored globally to prevent recursive processing loops.

---

# Folder Layout

```text
/data/
├── input/
├── output/
├── logs/
├── tmp/
└── config/
```

---

# Input Behavior

## Single File

If a single file is dropped into:

```text
/data/input/
```

the container automatically creates a run folder.

Example:

```text
/data/input/test.pdf
```

becomes:

```text
Run Name:
test
```

---

## Folder Input

Folders dropped into `/data/input` are processed recursively.

Each folder becomes a single run.

---

# Output Structure

Example:

```text
/output/MyRun/
├── MyRun.csv
├── run.log
├── run_summary.json
├── Mandatory Review/
└── extracted txt files
```

---

# CSV Format

The CSV schema is always:

```text
filename,page,text,method,used_ocr,reliability
```

---

# OCR Modes

## OCR-A

Balanced OCR mode:

- faster,
- lower resource usage,
- preferred first OCR fallback.

---

## OCR-B

Aggressive OCR mode:

- slower,
- more tolerant of poor scans,
- final OCR fallback before Mandatory Review.

---

# Large PDF Handling

Large PDFs automatically switch to per-page processing.

Thresholds:

```text
BIGPDF_SIZE_LIMIT_MB=50
BIGPDF_PAGE_LIMIT=500
```

---

# DEBUG_TEMP_MODE

Set:

```text
DEBUG_TEMP_MODE=true
```

to preserve temporary processing files after a run.

Useful for:

- OCR debugging,
- portfolio extraction debugging,
- temp-file troubleshooting.

Default:

```text
false
```

---

# Runtime Cleanup

The container automatically:

- removes completed portfolio stash folders,
- removes stale temporary extraction folders,
- cleans empty run folders,
- deletes successful inputs.

Cleanup behavior respects:

```text
DEBUG_TEMP_MODE
```

---

# Run Summary Reporting

Each run generates:

```text
/output/<run>/run_summary.json
```

This includes:

- files seen
- files processed
- files accepted
- Manual Review counts
- ignored files
- cleanup actions
- pass failures
- unsupported files

---

# Logging

Main logs:

```text
/output/<run>/run.log
/data/logs/docker.log
```

Additional logging includes:

- OCR stage transitions,
- portfolio extraction mapping,
- Manual Review moves,
- cleanup operations,
- reliability decisions.

---

# Environment Variables

## Core Paths

```text
INPUT_DIR=/data/input
OUTPUT_DIR=/data/output
WORK_DIR=/data/tmp
LOG_DIR=/data/logs
CONFIG_DIR=/data/config
```

---

## Processing Thresholds

```text
PASS_TXT_CUTOFF=0.75
PASS_DOC_CUTOFF=0.75
PASS_OCR_A_CUTOFF=0.65
PASS_OCR_B_CUTOFF=0.55
```

---

## Runtime Controls

```text
DEBUG_TEMP_MODE=false
INPUT_STABLE_SECS=15
INPUT_CHECK_INTERVAL=15
```

---

## Permissions

```text
PUID=99
PGID=100
UMASK=0002
```

Designed for:

- UnRAID
- Docker bind mounts
- SMB shares

---

# Docker Example

```yaml
services:
  document-extractor:
    image: strahdzarovich/document-extractor:0.1.9
    container_name: document-extractor

    environment:
      - PUID=99
      - PGID=100
      - TZ=America/New_York

    volumes:
      - /mnt/user/document-extractor:/data
      - /mnt/user/document-extractor/tmp:/data/tmp

    restart: unless-stopped
```

---

`/data/tmp` is shown as a separate bind mount on purpose. This makes it easy to move temporary OCR/portfolio/Office work to faster or disposable storage without moving the full `/data` folder.

---

# Current Limitations

## Long Embedded Filenames

0.1.9 adds automatic filename shortening for deeply nested embedded files.

Shortened filenames preserve:

- extensions
- readability
- collision resistance via short hashes

Forensic lineage is preserved separately through:

- portfolio_manifest.csv
- review_manifest.csv

Additional validation is still ongoing for:

- extremely deep nested attachments
- Windows SMB edge cases
- archive extraction edge cases

---

## XLSX Handling

`.xlsx` currently routes to Mandatory Review.

Future versions may add:

- lightweight extraction,
- OCR conversion fallback,
- sheet text extraction.

---

# Recommended Workflow

1. Drop files/folders into:

```text
/data/input/
```

2. Wait for processing to complete.

3. Review:

- CSV output,
- TXT files,
- Mandatory Review,
- run.log,
- run_summary.json.

4. Adjust config rules as needed.

---

# Version Notes

## 0.1.9 Highlights

- Added centralized filename policy system
- Added automatic long-filename shortening
- Added forensic lineage metadata tracking
- Added lineage-aware portfolio manifests
- Added centralized review manifest handling
- Added run_summary.json reporting
- Added run-level cleanup/process counters
- Improved architecture separation between:
  - orchestration
  - filename policy
  - lineage tracking
  - manifest writing
  - reporting
- Confirmed portfolio extraction stability during large mixed-document testing

---

## 0.1.8 Highlights

- Fixed Mandatory Review temp-name issues
- Preserved logical embedded filenames
- Added safe portfolio lineage naming
- Added configurable extension handling
- Added render_page_image() OCR helper
- Reduced OCR renderer fallback spam
- Added DEBUG_TEMP_MODE
- Improved runtime cleanup handling
- Improved portfolio extraction traceability
- Improved embedded Office handling