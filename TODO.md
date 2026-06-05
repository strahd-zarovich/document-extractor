# TODO

## Done (0.1.8 → 0.1.9)

### Filename Length / Path Safety
- Added centralized filename policy helper:
  - `scripts/filename_policy.py`
- Added safe filename sanitization for extracted/embedded files
- Added filename length limiting to prevent Windows / SMB / path-length failures
- Preserved file extensions when shortening long filenames
- Added stable hash suffixes for shortened filenames
- Integrated filename policy into portfolio extraction
- Preserved readable physical filenames while avoiding unusable long paths

### Forensic Lineage / Portfolio Traceability
- Added centralized lineage helper:
  - `scripts/lineage.py`
- Added forensic parent-child path metadata
- Preserved original full generated names outside the physical filename
- Added readable portfolio path format:
  - `Parent PDF / Embedded PDF / Attachment`
- Integrated lineage metadata into `portfolio_manifest.csv`
- Confirmed portfolio manifests are ignored by normal processing
- Confirmed extracted portfolio children are processed normally

### Review Manifest Standardization
- Added centralized review manifest helper:
  - `scripts/review_manifest.py`
- Centralized `review_manifest.csv` writing
- Added normalized Manual Review reason handling
- Expanded review manifest metadata support:
  - filename
  - reason
  - portfolio_path
  - original_full_name
- Kept `process_run.py` focused on orchestration instead of manifest formatting

### Run Summary / Reporting
- Added centralized run summary helper:
  - `scripts/run_summary.py`
- Added run-level counters for:
  - files seen
  - files processed
  - files accepted
  - files deleted after success
  - files moved to Manual Review
  - unsupported files
  - ignored files
  - noise-deleted files
  - pass failures
  - missing pass scripts
  - cleanup actions
- Added run-end summary logging
- Added `run_summary.json` output

### Runtime / Logging Cleanup
- Identified harmless startup permission noise from bind-mounted config files
- Planned stderr suppression for best-effort `chgrp/chmod` startup permission normalization
- Confirmed OCR renderer helper is working during large-file testing
- Confirmed `.ptx` noise-delete policy works during live run testing
- Confirmed `.doc` Manual Review routing works during live run testing

## Done (0.1.7 → 0.1.8)

### Manual Review / Filename Preservation
- Fixed Mandatory Review naming fallback logic
- Preserved logical/original filenames when moving files to Mandatory Review
- Prevented random temp names / 8.3-style names like C3XWAM~P from becoming final review filenames
- Added safer Mandatory Review filename cleanup for invalid filesystem characters
- Added duplicate-name protection when moving files to Mandatory Review
- Added [MANUAL_MOVE] logging for troubleshooting review moves

### Config / File Rule Lists
- Fixed config list loading so filename ignore lists are not treated like extensions
- Confirmed existing in-place config files are not overwritten during rebuilds
- Added README note: /data/config files are user-owned and not overwritten by defaults
- Added/confirmed delete rules for:
  - .msg
  - .pptx
  - .ptx
  - .wav
- Added/confirmed ignore rules for:
  - portfolio_manifest.csv
  - review_manifest.csv
  - .processed.list
- Confirmed .doc and .xlsx route to Manual Review by default

### Portfolio / Embedded Extraction
- Replaced unsafe portfolio child naming using "::" with "__"
- Preserved parent-child lineage in extracted embedded filenames
- Added filesystem-safe naming for extracted portfolio children
- Added portfolio child mapping logs
- Added successful pdfdetach extraction logging
- Added internal manifest skip handling inside portfolio extraction
- Confirmed extracted embedded Office files now use readable parent-based names

### OCR / Rendering
- Added common.render_page_image()
- Standardized renderer helper signature for OCR-A/OCR-B
- Reduced OCR renderer fallback spam from incompatible helper signatures
- Kept existing internal fitz renderer fallback as backup

### Cleanup / Runtime Stability
- Added DEBUG_TEMP_MODE support
- Added run-scoped portfolio stash cleanup guard
- Added startup cleanup check for old portfolio_hidden folders
- Moved DOC→PDF temp work under configured WORK_DIR/office
- Improved traceability of temp/runtime cleanup behavior

### Bug Fixes / Code Cleanup
- Removed duplicate empty-run-folder cleanup block in process_run.py
- Removed bad top-level chmod(path) block from common.py
- Restored run.log group-writable chmod in the correct logging helper
- Corrected Manual Review reason passing for unsupported, pass_script_missing, and pass rc failures
- Confirmed permissions issue is fixed in 0.1.8 testing

---

## Done (0.1.6 → 0.1.7)

### Core OCR / Extraction Pipeline
- Added multi-pass OCR processing flow
- Added OCR-A / OCR-B reliability comparison logic
- Added TXT acceptance scoring and reliability tracking
- Added page-level extraction fallback handling
- Added OCR-required forcing of per-page extraction rows
- Added image-file OCR support improvements
- Added better PDF text-vs-image detection
- Added improved fallback handling for low-text PDFs
- Added multi-stage extraction decision flow:
  - TXT
  - OCR
  - image fallback
  - manual review
- Added OCR confidence/reliability scoring into CSV output
- Added improved CSV reporting structure

### Docker / Runtime Stability
- Reworked container structure to match newer document-extractor layout
- Added improved logging structure
- Added daily log rotation support
- Added expanded debug logging throughout extraction flow
- Added startup cleanup handling
- Added stale lock cleanup on startup
- Added lock protection between analyze / clear_analyze operations
- Added better temp directory cleanup handling
- Added WORK_DIR free-space protection checks
- Added configurable config.conf handling instead of .env reliance
- Added improved container compatibility for UnRAID
- Preserved existing UnRAID variable compatibility

### File Handling / Workflow
- Added one TXT file per source document workflow
- Added metadata headers inside TXT outputs
- Added page separator formatting:
  === [PAGE N] ===
- Added single-row-per-document CSV reporting
- Added better processed.list handling
- Added recursive extraction handling improvements
- Added review_manifest.csv handling
- Added quarantine/Manual Review flow
- Added delete-on-success workflow
- Added ignore/delete extension handling framework
- Added `.wav` automatic deletion handling
- Added `.ptx` delete handling
- Added `.pptx` delete handling
- Added better unsupported-file detection
- Added portfolio_hidden workflow for portfolio extraction
- Added reduced portfolio extraction log noise

### OCR / Rendering Improvements
- Added internal fitz renderer fallback
- Added render fallback logic when OCR renderer fails
- Added safer OCR exception handling
- Added better image rendering recovery handling
- Added support groundwork for common.render_page_image()

### Office / Embedded File Handling
- Added embedded file extraction groundwork
- Added portfolio extraction support
- Added spreadsheet detection handling
- Added spreadsheet Manual Review routing
- Added embedded Office artifact detection improvements
- Added handling for unsupported Office extraction cases

### Logging / Diagnostics
- Added reliability score reporting
- Added detailed OCR logging
- Added extraction-path logging
- Added failure-path logging
- Added processing-state logging
- Added improved unsupported-file reporting
- Added expanded debug logging for OCR fallback behavior

### Cleanup / Processing Safety
- Added delete-on-success cleanup
- Added quarantine-on-failure behavior
- Added review_manifest.csv generation
- Added partial extraction cleanup improvements
- Added better handling for interrupted runs
- Added startup cleanup of stale locks/files

### WebUI / Future Framework
- Added initial WebUI structural groundwork
- Added settings framework planning
- Added support structure for future WebUI controls

### Bug Fixes / Stability Fixes
- Reduced repeated OCR fallback exception spam
- Improved handling of unsupported extraction artifacts
- Reduced recursive processing issues
- Improved stability on malformed PDFs
- Improved handling of corrupt embedded Office artifacts
- Improved processing stability on mixed-content PDFs
- Improved handling of image-only PDFs
- Improved handling of large OCR workloads
- Fixed several container startup/runtime edge cases

---

## Done (0.1.5)
- Portfolio parents moved to WORK_DIR/portfolio_hidden (no dotfiles left in /data/input)
- Quiet portfolio logs via PORTFOLIO_AUTORUN_ANNOUNCE
- OCR-required → force per-page rows (even for small PDFs)
- Reliability score in every row (TXT/DOC/IMG/OCR)
- Free-space guardrail (<1 GB in WORK_DIR → fail file early to Manual Review)
- Delete-on-success; quarantine on failure with review_manifest.csv
- Initial noise delete handling exists, currently `.wav`

---

## Planned Roadmap

### 0.1.10 — Config + Logging Polish

#### Startup Config Logging
- Print actual active config values from:
  - `config.conf`
  - environment variables
- Expand startup cutoff banner to distinguish:
  - DOC cutoff
  - DOCX cutoff
- Prevent confusion during runtime log review
- Ensure startup logging reflects runtime-configured values instead of static text

#### Startup Permission Noise
- Suppress harmless startup permission errors from bind-mounted config files:
  - `chgrp: Operation not permitted`
  - `chmod: Operation not permitted`
- Keep permission normalization best-effort only
- Add comments explaining some bind mounts do not allow ownership/permission changes

#### Documentation Alignment
- Keep README, TODO, and defaults aligned
- Verify Office handling documentation matches actual behavior:
  - `.doc`   -> Manual Review
  - `.xlsx`  -> Manual Review
  - `.pptx`  -> Delete
  - `.ptx`   -> Delete
  - `.msg`   -> Delete

---

### 0.1.11 — Failure Metadata

#### Manual Review / Failure Handling
- Continue standardizing Manual Review reasons:
  - pass_rc
  - unsupported_ext
  - low_workdir_space
  - timeout
  - doc_manual_review
  - spreadsheet_manual_review
  - temp_processing_failure
  - embedded_extract_failure
  - corrupt_pdf
  - bad_magic
  - partial_attachment
  - invalid_container
  - mismatched_extension

#### Failure Sidecar Metadata
- Add optional sidecar failure metadata files:
  - `filename.failed.json`
- Include:
  - source file
  - original full filename
  - normalized filename
  - original extension
  - normalized extension
  - detected MIME type
  - detected magic-byte type
  - portfolio path
  - embedded filename
  - extraction method
  - temp path
  - failure reason
  - traceback if available

#### Integration Goals
- Integrate with:
  - `filename_policy.py`
  - `lineage.py`
  - `review_manifest.py`

#### TXT Header Lineage
- Add forensic source lineage to the top of generated TXT files
- Include:
  - source file
  - original full filename
  - normalized filename
  - original extension
  - normalized extension
  - detected MIME type
  - detected magic-byte type
  - portfolio path
  - embedded parent
  - embedded child
  - extraction source/type
- Goal:
  - allow each TXT file to stand alone as evidence-traceable output
  - make it easy to answer: “Where did this document come from?”

---

### 0.1.12 — Cleanup Recovery

#### Cleanup / Processing Control
- Improve cleanup reliability after exceptions:
  - remove orphan temp files
  - remove partial extraction dirs
  - remove abandoned temp artifacts

#### Interrupted Run Recovery
- Add interrupted-run cleanup handling
- Detect abandoned extraction folders
- Detect stale temp artifacts

#### Cleanup Reporting
- Expand cleanup reporting summary:
  - temp files created
  - temp files deleted
  - orphan temp files removed
  - failed cleanup attempts

#### Ignored Manifest Cleanup
- Delete known ignored artifacts automatically:
  - `portfolio_manifest.csv`
  - abandoned extraction manifests
  - stale processing markers
- Remove empty `__portfolio` folders automatically
- Improve empty directory cleanup reliability
- Prevent ignored-file cleanup loops

#### DEBUG_TEMP_MODE
- Add optional DEBUG_TEMP_MODE temp-folder reporting/viewer

---

### 0.1.13 — Portfolio / Embedded Statistics

#### Portfolio / Embedded Extraction
- Add persistent temp-file metadata registry:
  - temp path
  - source file
  - embedded filename
  - final output filename
  - extraction source

#### Expanded Extraction Lineage
- Expand extraction lineage tracking:
  Example:
    Parent PDF
      -> embedded XLSX
        -> converted PDF
          -> OCR TXT

#### Embedded Attachment Statistics
- Add embedded attachment extraction statistics:
  - extracted attachments
  - attachment types
  - failures
  - Manual Review moves

#### Embedded Artifact Classification
- Track:
  - malformed attachments
  - duplicate collision artifacts
  - encrypted content
  - forensic export artifacts
  - partial container exports
- Examples:
  - `.rpmsg`
  - `.pdf_8`
  - `.xmef`

#### Portfolio Reporting
- Add portfolio extraction statistics:
  - total portfolios processed
  - embedded attachment counts
  - embedded extraction failures
  - attachment-type distribution

---

### 0.1.14 — Validation + Reporting

#### Validation / Performance
- Add golden test set + quick validation script
- Add per-file processing summary output
- Add extraction pipeline timing statistics

#### Unsupported File Reporting
- Add better unsupported-file reporting:
  - group by extension/type
  - reduce repetitive log spam

#### Extension Distribution Reporting
- Add grouped extension statistics:
  - extension frequency
  - unsupported extension counts
  - Manual Review grouped by extension
  - corrupt file counts
  - normalized filename counts

#### OCR Escalation Reporting
- Add OCR-stage statistics:
  - native accepted
  - OCR escalated
  - OCR accepted
  - OCR rejected
  - borderline reliability files

#### Reporting Improvements
- Add expanded extraction timing visibility
- Add extraction-stage statistics
- Add reliability-distribution reporting

---

### 0.1.15 — Office / XLSX Handling

#### DOC / XLSX / Office Handling
- Decide final `.xlsx` handling:
  - lightweight extraction with openpyxl, or
  - Manual Review

#### XLSX Extraction
- If enabled:
  - create `pass_xlsx.py`
  - keep XLSX extraction lightweight and isolated
- Initial scope:
  - workbook metadata
  - sheet names
  - row counts
  - lightweight text extraction
  - hidden sheet detection

#### DOC Handling
- Decide whether old `.doc` should stay Manual Review permanently

#### Stability Requirement
- Delay XLSX extraction support until:
  - forensic metadata system is stable
  - validation framework is mature

---

### 0.1.16 — OCR / Rendering Performance

#### OCR / Rendering / Performance
- Add image render cache between OCR-A and OCR-B
- Add optional detailed OCR confidence reporting

#### OCR Escalation Threshold Tuning
- Review OCR escalation comparison logic:
  - `<= cutoff`
  - vs `< cutoff`
- Reduce unnecessary OCR escalation for borderline files

#### Parallel OCR
- Add parallel OCR for large PDFs with capped concurrency
- Keep memory usage bounded and predictable

#### Validation / Performance
- Add checksum cache to skip reprocessing duplicates

---

### 0.1.17+ — WebUI

#### WebUI
- WebUI thin control panel:
  - upload files/folders into `/appdata/input`
  - trigger existing scripts
  - show logs/status
  - download zipped `/appdata/output`

#### WebUI Rule Management
- Add WebUI editor for file-rule lists later:
  - delete extensions
  - ignore files
  - manual review extensions

#### Long-term Goals
- Keep WebUI thin and orchestration-focused
- Avoid embedding extraction logic into the frontend

---

### 0.1.18+ — Forensic Dataset Support

#### Legal / eDiscovery Dataset Awareness
- Add awareness/support for:
  - forensic export artifacts
  - Outlook export remnants
  - Teams exports
  - attachment collision artifacts
  - encrypted/protected Office files
  - partial container recovery

#### Forensic Artifact Routing
- Add routing awareness for:
  - `.lef`
  - `.sbf`
  - `.xmef`
  - `.rpmsg`
- Improve Manual Review classification visibility

#### Optional Salvage Tools
- Future optional recovery support:
  - qpdf repair
  - Ghostscript rewrite
  - mupdf clean
  - ZIP recovery checks
  - Office repair attempts