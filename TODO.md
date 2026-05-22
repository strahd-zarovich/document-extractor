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
- Run-scoped cleanup: remove WORK_DIR/portfolio_hidden/<run> at “Run end”
- Optional startup/end-of-cycle sweep of WORK_DIR/portfolio_hidden
- Standardize Manual Review reasons: pass_rc, unsupported_ext, low_workdir_space, timeout, doc_manual_review, spreadsheet_manual_review, etc.
- Version banner: echo Poppler/Tesseract/Python package versions at startup
- Add configurable file-rule lists:
  - delete extensions
  - ignore extensions
  - manual-review extensions
  - supported/process extensions
- Add `.msg` to delete list
- Move `.doc` files to Manual Review instead of attempting DOC→PDF conversion
- Decide final `.xlsx` handling:
  - lightweight extraction with openpyxl, or
  - Manual Review
- Silence/ignore `portfolio_manifest.csv`

## Optional enhancements
- Parallel OCR for large PDFs with capped concurrency
- Image render cache between OCR-A and OCR-B
- Checksum cache to skip reprocessing duplicates
- Golden test set + quick validation script
- WebUI thin control panel:
  - upload files/folders into `/appdata/input`
  - trigger existing scripts
  - show logs/status
  - download zipped `/appdata/output`
- WebUI editor for file-rule lists later