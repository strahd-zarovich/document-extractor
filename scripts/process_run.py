#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run orchestrator:
 - Recursively walk a run directory
 - Ensure a single CSV index for the run
 - Route each file to its pass
 - On success: write CSV and DELETE source
 - On failure/unsupported: move to Mandatory Review and record reason
"""
import os, sys, csv, subprocess
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import common

CSV_HEADER = [
    "original_file",
    "original_name",
    "relative_path",
    "txt_relative_path",
    "pages",
    "processed_at",
    "pass_used",
    "score",
    "status",
    "used_ocr",
    "run_id",
    "notes",
]
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "/data/config"))

def _load_list_file(filename: str, defaults: set[str], add_dot: bool = True) -> set[str]:
    path = CONFIG_DIR / filename
    if not path.exists():
        return defaults

    values = set()
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lower()
                if not line or line.startswith("#"):
                    continue

                # Extension lists need leading dots.
                # Filename ignore lists must keep exact filenames.
                if add_dot and not line.startswith(".") and "*" not in line:
                    line = "." + line

                values.add(line)
    except Exception:
        return defaults

    return values

SUPPORTED_EXTS = {".pdf", ".docx", ".txt", ".tif", ".tiff", ".png", ".jpg", ".jpeg"}

NOISE_DELETE_EXTS = _load_list_file(
    "delete_extensions.txt",
    {".wav", ".msg", ".pptx", ".ptx"},
    add_dot=True,
)

IGNORE_FILES = _load_list_file(
    "ignore_files.txt",
    {"portfolio_manifest.csv", "review_manifest.csv", ".processed.list"},
    add_dot=False,
)

MANUAL_REVIEW_EXTS = _load_list_file(
    "manual_review_extensions.txt",
    {".doc", ".xlsx"},
    add_dot=True,
)

def _ensure_dirs(run_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "Mandatory Review").mkdir(parents=True, exist_ok=True)
    # NEW: ensure setgid + group-writable on run output dirs
    try:
        os.chmod(out_dir, 0o2775)  # drwxrwsr-x
    except Exception:
        pass
    try:
        os.chmod(out_dir / "Mandatory Review", 0o2775)
    except Exception:
        pass

def _csv_path_for_run(run_name: str, out_dir: Path, single_file_name: str = None) -> Path:
    if single_file_name:
        return out_dir / f"{single_file_name}.csv"
    return out_dir / f"{run_name}.csv"

def _write_header_if_needed(csv_path: Path):
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADER)
        # NEW: ensure group-writable file mode on first creation
        try:
            os.chmod(csv_path, 0o664)
        except Exception:
            pass

def _append_review_manifest(out_dir: Path, relpath: str, reason: str):
    manifest = out_dir / "review_manifest.csv"
    new = not manifest.exists()
    with manifest.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["filename", "reason"])
        w.writerow([relpath, reason])
    if new:
        # NEW: ensure group-writable file mode when first created
        try:
            os.chmod(manifest, 0o664)
        except Exception:
            pass

def _call_script(script: str, args: List[str]) -> int:
    cmd = [sys.executable, script] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Mirror stdout/stderr to the console for visibility
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode

def _route_ext(path: Path) -> str:
    fname = path.name.lower()
    ext = path.suffix.lower()

    if fname in IGNORE_FILES:
        return "ignore"

    if ext in NOISE_DELETE_EXTS:
        return "noise_delete"

    if ext in MANUAL_REVIEW_EXTS:
        return "manual_review"

    if ext not in SUPPORTED_EXTS:
        return "unsupported"

    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "doc"
    if ext == ".txt":
        return "txt"
    if ext in (".tif", ".tiff", ".png", ".jpg", ".jpeg"):
        return "img"

    return "unsupported"

def _is_single_file_run(run_dir: Path) -> Optional[str]:
    # If the run contains exactly one *processable* file at top-level, use its stem.
    # Exclude 'unsupported' and 'noise_delete' (e.g., .wav).
    PROCESSABLE = {"pdf", "doc", "txt", "img"}
    entries = []
    for p in run_dir.iterdir():
        if not p.is_file():
            continue
        kind = _route_ext(p)
        if kind in PROCESSABLE:
            entries.append(p)
    return entries[0].stem if len(entries) == 1 else None

def _delete_path(p: Path):
    try:
        p.unlink()
    except Exception:
        pass

def main():
    if len(sys.argv) < 4:
        print("usage: process_run.py <run_dir> <output_dir> <run_log_path>", file=sys.stderr)
        sys.exit(2)

    run_dir = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    run_log_path = sys.argv[3]

    logger = common.get_logger(run_log_path)
    _ensure_dirs(run_dir, output_dir)

    run_name = run_dir.name
    single_file_name = _is_single_file_run(run_dir)
    csv_path = _csv_path_for_run(run_name, output_dir, single_file_name)
    _write_header_if_needed(csv_path)

    logger.info(f"Run start: {run_name}")

    # Walk the tree (skip Mandatory Review)
    for root, dirs, files in os.walk(run_dir):
        # Don't descend into Mandatory Review folders if any
        dirs[:] = [d for d in dirs if d.lower() != "mandatory review"]
        for fname in files:
            fpath = Path(root) / fname
            relpath = str(fpath.relative_to(run_dir))
            kind = _route_ext(fpath)

            if kind == "noise_delete":
                logger.info(f"Noise file (auto-delete): {relpath}")
                try:
                    _delete_path(fpath)
                except Exception:
                    logger.warning(f"Failed to delete noise file: {relpath}")
                continue

            if kind == "ignore":
                logger.info(f"Ignored file: {relpath}")
                continue

            if kind == "manual_review":
                logger.warning(f"Manual Review file type: {relpath}")
                _append_review_manifest(output_dir, relpath, "manual_review_ext")
                common.move_to_manual(
                    str(fpath),
                    str(output_dir),
                    "manual_review_ext",
                    original_relpath=relpath,
                )
                continue

            if kind == "unsupported":
                logger.warning(f"Unsupported file: {relpath}")
                _append_review_manifest(output_dir, relpath, "unsupported")
                # Move to MR
                common.move_to_manual(
                    str(fpath),
                    str(output_dir),
                    "unsupported",
                    original_relpath=relpath,
                )
                continue

            # Decide target script
            if kind == "pdf":
                script = Path(SCRIPT_DIR) / "pass_pdf.py"
            elif kind == "doc":
                script = Path(SCRIPT_DIR) / "pass_doc.py"
            elif kind == "txt":
                script = Path(SCRIPT_DIR) / "pass_txt.py"
            elif kind == "img":
                script = Path(SCRIPT_DIR) / "pass_img.py"
            else:
                script = None

            if not script or not script.exists():
                logger.error(f"Pass script missing for {relpath}: {script}")
                _append_review_manifest(output_dir, relpath, "pass_script_missing")
                common.move_to_manual(
                    str(fpath),
                    str(output_dir),
                    "pass_script_missing",
                    original_relpath=relpath,
                )
                continue

            # Call the pass
            rc = _call_script(str(script), [str(fpath), str(csv_path), str(run_log_path)])

            if rc == 0:
                # success -> DELETE source
                _delete_path(fpath)
                logger.info(f"Accepted & deleted: {relpath}")
            else:
                # failed -> Mandatory Review with reason
                reason = f"pass rc={rc}"
                logger.warning(f"Quarantining: {relpath} :: {reason}")
                _append_review_manifest(output_dir, relpath, reason)
                common.move_to_manual(
                    str(fpath),
                    str(output_dir),
                    reason,
                    original_relpath=relpath,
                )

    # Prune empty subfolders in the run
    for root, dirs, files in os.walk(run_dir, topdown=False):
        p = Path(root)
        if p == run_dir:
            continue
        try:
            if not any(Path(root).iterdir()):
                p.rmdir()
        except Exception:
            pass

    # --- Remove empty run folder (avoid leaving ghost dirs that trigger re-scans) ---
    try:
        run_dir_p = Path(run_dir).resolve()
        input_root = Path(os.getenv("INPUT_DIR", "/data/input")).resolve()

        # Best-effort: remove common junk files that would keep the dir non-empty
        for junk in (".DS_Store", "Thumbs.db"):
            try:
                (run_dir_p / junk).unlink()
            except FileNotFoundError:
                pass
            except Exception:
                pass

        # Only remove if:
        #  - it's NOT the input root itself
        #  - its parent IS the input root
        #  - it is empty
        if run_dir_p != input_root and run_dir_p.parent == input_root:
            try:
                next(run_dir_p.iterdir())
                is_empty = False
            except (StopIteration, FileNotFoundError):
                is_empty = True
            if is_empty:
                logger.info(f"Input cleanup: removing empty run folder: {run_dir_p.name}")
                try:
                    run_dir_p.rmdir()
                except Exception as e:
                    logger.debug(f"Input cleanup: could not remove {run_dir_p}: {e}")
    except Exception as e:
        logger.debug(f"Input cleanup failed: {e}")

    # --- Clean the portfolio stash for THIS run (if any) ---
    try:
        work_dir = Path(os.environ.get("WORK_DIR", "/data/tmp")).resolve()
        input_dir = Path(os.environ.get("INPUT_DIR", "/data/input")).resolve()
        run_abs = Path(run_dir).resolve()

        # Compute stash dir relative to INPUT_DIR (guard against ValueError)
        try:
            rel = run_abs.relative_to(input_dir)
        except Exception:
            rel = run_abs.name  # fallback: just use the folder name

        stash_dir = work_dir / "portfolio_hidden" / rel

        # v0.1.8:
        # DEBUG_TEMP_MODE keeps portfolio stash files for inspection after a run.
        # Normal mode still removes the run-specific stash to avoid old parent PDFs piling up.
        if os.getenv("DEBUG_TEMP_MODE", "false").lower() == "true":
            logger.info(f"DEBUG_TEMP_MODE=true; keeping portfolio stash for inspection: {stash_dir}")
        elif stash_dir.exists():
            shutil.rmtree(stash_dir, ignore_errors=True)
            logger.info(f"Cleaned portfolio stash: {stash_dir}")
    except Exception as e:
        logger.warning(f"Stash cleanup skipped: {e}")

    logger.info(f"Run end: {run_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
