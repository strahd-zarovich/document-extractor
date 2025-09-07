
---

# Updated `TODO.md` (complete)

```markdown
# TODO

## Pipeline Correctness / Policy
- [X] **Auto-delete `.wav`** on sight (log + delete), do **not** send to Manual Review.
- [ ] **Legacy shell scripts cleanup:** remove unused `pass_*.sh` to avoid confusion; Python passes are authoritative.
- [ ] **Explicit mode log:** include `mode=per-doc|per-page` with the triggering condition (size/pages) on every PDF (partially present; standardize message).
- [ ] **Consistent method strings:** audit any caller/consumer assumptions about `pdf_text|pdf_ocr_a|pdf_ocr_b|docx_text|doc_text|txt|img_ocr`.

## Observability / UX
- [ ] **Structured errors:** Standardize Manual Review reasons (`pass_rc`, `unsupported_ext`, `low_workdir_space`, `pass_script_missing`).
- [ ] **Version banner:** expand startup version echo to include Poppler/Tesseract binaries (paths + `--version` output).
- [ ] **Metrics (optional):** track per-run totals (accepted, quarantined, per-pass accept counts, median reliability).

## Performance
- [ ] **Parallel OCR (optional):** page-level parallelism for large PDFs (respect CPU cores minus one; cap concurrency).
- [ ] **Image cache (optional):** if page rasterization is retried across OCR-A/B, consider sharing rendered images via WORK_DIR.
- [ ] **Sampling pre-pass:** on huge PDFs, consider sampling early to reject clearly hopeless files faster.

## Robustness
- [ ] **Timeouts:** per-page and per-file soft timeouts; if exceeded, continue with best-effort and mark reason in MR.
- [ ] **OOM guard:** detect low memory conditions (if feasible) and downgrade DPI or bail out with `low_memory` reason.
- [ ] **Checksum dedupe:** optional SHA-256 cache to skip reprocessing identical files across runs.

## Config & Docs
- [ ] **README drift:** keep the **Per-doc vs Per-page** and **Reliability** sections up to date when thresholds change.
- [ ] **Sample corpus:** maintain a small set of test files in `docs/samples/` with expected outcomes for quick validation.
- [ ] **Changelog:** start a simple `CHANGELOG.md` for operational changes (cutoffs, thresholds, dependency pins).

## Dependency Hygiene
- [ ] **Package review:** keep only what is used (Poppler utils, Tesseract, PyMuPDF, python-docx, antiword/catdoc, Pillow, pdfminer.six if needed).
- [ ] **Pin & log versions:** PyMuPDF, pdfminer.six, Pillow, pytesseract; ensure no duplicate providers (e.g., avoid mixing `python3-pdfminer` apt with `pdfminer.six` pip).
- [ ] **Healthcheck parity:** ensure `/app/scripts/healthcheck.sh` reflects readiness (dirs + perms), not workload.

## Testing
- [ ] **Golden tests:** a handful of PDFs (native + scan + hybrid), DOC/DOCX, TXT, and images; assert CSV shape and reliability ranges.
- [ ] **Large-file test:** a ≥100 MB PDF (image-heavy) to verify per-page mode, disk guard, and resource stability.
- [ ] **Noise test:** various unsupported types (xls/xlsx, zip, mp3, wav) to confirm policy (delete/quarantine).

