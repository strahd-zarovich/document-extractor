# TODO

## Done (0.1.5)
- Portfolio parents moved to WORK_DIR/portfolio_hidden (no dotfiles left in /data/input)
- Quiet portfolio logs via PORTFOLIO_AUTORUN_ANNOUNCE
- OCR-required → force per-page rows (even for small PDFs)
- Reliability score in every row (TXT/DOC/IMG/OCR)
- Free-space guardrail (<1 GB in WORK_DIR → fail file early to Manual Review)
- Delete-on-success; quarantine on failure with review_manifest.csv

## Near-term
- Run-scoped cleanup: remove WORK_DIR/portfolio_hidden/<run> at “Run end”
- (Optional) Startup/end-of-cycle sweep of WORK_DIR/portfolio_hidden
- Standardize Manual Review reasons: pass_rc, unsupported_ext, low_workdir_space, timeout, etc.
- Version banner: echo Poppler/Tesseract versions at startup

## Optional enhancements
- Parallel OCR for large PDFs (cap concurrency)
- Image render cache between OCR-A and OCR-B
- Checksum cache to skip reprocessing duplicates
- Golden test set + quick validation script
- Explicit ignore/mark for `.msg` (if desired later)
