# TODO

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

## Near-term

### Filename Length / Path Safety
- Add filename length limiting for extracted portfolio / embedded files
- Preserve file extension when shortening long names
- Preserve useful parent-child lineage while avoiding unusable long filenames
- Add suffix marker for shortened names, such as:
  - __CUT
  - __TRUNC
- Consider adding short hash suffix to avoid collisions
- Apply filename length safety in:
  - common.py
  - portfolio_unpack.py
- Goal:
  - prevent files from failing to open due to Windows / SMB / path length issues

### Manual Review / Failure Handling
- Standardize Manual Review reasons:
  - pass_rc
  - unsupported_ext
  - low_workdir_space
  - timeout
  - doc_manual_review
  - spreadsheet_manual_review
  - temp_processing_failure
  - embedded_extract_failure
- Add sidecar failure metadata files:
  - filename.failed.json
  - include:
    - source file
    - embedded filename
    - extraction method
    - temp path
    - failure reason
    - traceback if available

### Cleanup / Processing Control
- Improve cleanup reliability after exceptions:
  - remove orphan temp files
  - remove partial extraction dirs
  - remove abandoned temp artifacts
- Add cleanup reporting summary:
  - temp files created
  - temp files deleted
  - orphan temp files removed
  - failed cleanup attempts

### DOC / XLSX / Office Handling
- Decide final `.xlsx` handling:
  - lightweight extraction with openpyxl, or
  - Manual Review
- Decide whether old `.doc` should stay Manual Review permanently
- Keep `.pptx`, `.ptx`, and `.msg` deleted unless future use-case changes

### Portfolio / Embedded Extraction
- Add persistent temp-file metadata registry:
  - temp path
  - source file
  - embedded filename
  - final output filename
  - extraction source
- Add extraction lineage tracking:
  Example:
    Parent PDF
      -> embedded XLSX
        -> converted PDF
          -> OCR TXT
- Add embedded attachment extraction statistics:
  - extracted attachments
  - attachment types
  - failures
  - Manual Review moves

### OCR / Rendering / Performance
- Add image render cache between OCR-A and OCR-B
- Parallel OCR for large PDFs with capped concurrency
- Add optional detailed OCR confidence reporting

### Validation / Performance
- Checksum cache to skip reprocessing duplicates
- Golden test set + quick validation script
- Add per-file processing summary output
- Add extraction pipeline timing statistics

### WebUI
- WebUI thin control panel:
  - upload files/folders into `/appdata/input`
  - trigger existing scripts
  - show logs/status
  - download zipped `/appdata/output`
- WebUI editor for file-rule lists later

---

## Optional enhancements
- Add stronger filename sanitization utility:
  - illegal characters
  - duplicate separators
  - long paths
  - Windows reserved names
- Add optional DEBUG_TEMP_MODE output viewer / temp folder report
- Add better unsupported-file reporting:
  - group by extension/type
  - reduce repetitive log spam