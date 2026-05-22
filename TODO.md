# TODO

## Done (0.1.5)
- Portfolio parents moved to WORK_DIR/portfolio_hidden (no dotfiles left in /data/input)
- Quiet portfolio logs via PORTFOLIO_AUTORUN_ANNOUNCE
- OCR-required → force per-page rows (even for small PDFs)
- Reliability score in every row (TXT/DOC/IMG/OCR)
- Free-space guardrail (<1 GB in WORK_DIR → fail file early to Manual Review)
- Delete-on-success; quarantine on failure with review_manifest.csv
- Initial noise delete handling exists, currently `.wav`

## Near-term

### Cleanup / Processing Control
- Run-scoped cleanup: remove WORK_DIR/portfolio_hidden/<run> at “Run end”
- Optional startup/end-of-cycle sweep of WORK_DIR/portfolio_hidden
- Improve cleanup reliability after exceptions:
  - remove orphan temp files
  - remove partial extraction dirs
  - remove abandoned temp artifacts
- Add cleanup reporting summary:
  - temp files created
  - temp files deleted
  - orphan temp files removed
  - failed cleanup attempts

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
- Fix Mandatory Review naming fallback logic:
  - preserve original embedded filenames
  - never use random temp names
  - never use 8.3 short filenames
  - avoid extensionless temp artifacts
- Add sidecar failure metadata files:
  - filename.failed.json
  - include:
    - source file
    - embedded filename
    - extraction method
    - temp path
    - failure reason
    - traceback if available

### File Rule Lists / Extension Handling
- Add configurable file-rule lists:
  - delete extensions
  - ignore extensions
  - manual-review extensions
  - supported/process extensions
- Add `.msg` to delete list
- Add `.pptx` to delete list
- Add `.ptx` to delete list
- Ignore internal processing files globally:
  - portfolio_manifest.csv
  - review_manifest.csv
  - .processed.list
- Add better unsupported-file reporting:
  - group by extension/type
  - reduce repetitive log spam

### DOC / XLSX / Office Handling
- Move `.doc` files to Manual Review instead of attempting DOC→PDF conversion
- Decide final `.xlsx` handling:
  - lightweight extraction with openpyxl, or
  - Manual Review
- Improve PPTX handling consistency:
  - embedded PPTX
  - native PPTX
  - portfolio PPTX
  - decide:
    - delete
    - lightweight extraction
    - OCR fallback
    - Manual Review

### Portfolio / Embedded Extraction
- Preserve embedded filenames during portfolio extraction
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
- Improve portfolio recursion control:
  - avoid recursive loops
  - avoid duplicate scans
  - avoid processing internal extraction artifacts
- Add embedded attachment extraction statistics:
  - extracted attachments
  - attachment types
  - failures
  - Manual Review moves

### OCR / Rendering
- Fix OCR renderer helper signature mismatch:
  - OCR currently falls back to internal fitz renderer
  - Causes repeated log spam:
    "using internal renderer (fitz) due to incompatible signature"
  - Verify common.render_page_image() calling convention
  - Reduce per-page exception/fallback overhead on large PDFs
- Add image render cache between OCR-A and OCR-B
- Parallel OCR for large PDFs with capped concurrency

### Temp File Tracking / Logging
- Add temp-file lifecycle logging:
  - [TEMP_CREATE]
  - [TEMP_MOVE]
  - [TEMP_RENAME]
  - [TEMP_DELETE]
  - [TEMP_MOVE_MANDATORY]
- Add temp-to-source mapping logs:
  - source file
  - embedded filename
  - temp filename
  - final output filename
- Add standardized temp directory structure:
  - /tmp/document-extractor/render
  - /tmp/document-extractor/ocr
  - /tmp/document-extractor/portfolio
  - /tmp/document-extractor/office
  - /tmp/document-extractor/review
- Add optional DEBUG_TEMP_MODE:
  - preserve temp files intentionally for debugging runs

### Validation / Performance
- Version banner:
  - echo Poppler/Tesseract/Python package versions at startup
- Checksum cache to skip reprocessing duplicates
- Golden test set + quick validation script

### WebUI
- WebUI thin control panel:
  - upload files/folders into `/appdata/input`
  - trigger existing scripts
  - show logs/status
  - download zipped `/appdata/output`
- WebUI editor for file-rule lists later

## Optional enhancements
- Add filename sanitization utility:
  - illegal characters
  - duplicate separators
  - long paths
  - Windows reserved names
- Add extraction pipeline timing statistics
- Add per-file processing summary output
- Add optional detailed OCR confidence reporting