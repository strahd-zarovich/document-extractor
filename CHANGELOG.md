# Changelog

## [0.2.0] — pending
- (Planned) Confirm large end-to-end run is clean
- (Planned) Enable/run “Run end” cleanup of WORK_DIR/portfolio_hidden/<run>
- (Planned) Expand startup version banner (Poppler/Tesseract CLI versions)

## [0.1.5] — 2025-09-17
### Added
- PDF portfolio preprocessor now moves parent portfolios to WORK_DIR/portfolio_hidden
  (keeps /data/input clean; still idempotent)
- Quiet mode for portfolio preprocessing (PORTFOLIO_AUTORUN_ANNOUNCE=false by default)
- OCR-required → per-page CSV rows (page-accurate pointers for scans)

### Changed
- Default reliability cutoffs: TXT=0.75, DOC=0.75, OCR_A=0.65, OCR_B=0.55
- Improved OCR robustness: internal renderer fallback; unified ocr_image() helper

### Fixed
- PDF page count via PyMuPDF with pdfinfo fallback
- Consistent 6-column CSV with reliability everywhere

## [0.1.4] — 2025-09-08
- TXT→OCR-A→OCR-B pass order with reliability gating
- Big-doc per-page switch (≥50 MB or ≥500 pages)
- Delete source on success; quarantine on failure
