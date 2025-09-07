#!/usr/bin/env python3
"""
process_run.py — orchestrate a single RUN_NAME
- Recursively find supported files under RUN_PATH
- Route each file to the correct pass
- Append into a single CSV per run (or per single doc)
- Delete source files on success; prune empty dirs
Exit codes: 0=ok
"""
from __future__ import annotations
import os, sys, subprocess, shutil

# Pass routing for formats we actually process
SUPPORTED_EXT = {
    ".pdf":  "pass_pdf.sh",
    ".docx": "pass_doc.sh",
    ".doc":  "pass_doc.sh",    # antiword path handled inside the sh
    ".txt":  "pass_txt.sh",
    ".png":  "pass_img.sh",
    ".jpg":  "pass_img.sh",
    ".jpeg": "pass_img.sh",
    ".tif":  "pass_img.sh",
    ".tiff": "pass_img.sh",
}

# Extensions we do NOT process → always move to Mandatory Review
REVIEW_EXT = {
    ".xlsx",  # Excel is review-only by design
    # ".xls",  # uncomment if you want old Excel treated the same
}

def log(level, msg):
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def env(name, default=""):
    return os.getenv(name, default)

def iter_files(root: str):
    """Yield files under root, recursively, including REVIEW_EXT; skip hidden & MR."""
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if not d.startswith(".") and d != "Mandatory Review"]
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in SUPPORTED_EXT or ext in REVIEW_EXT:
                yield os.path.join(dp, fn)

def main() -> int:
    run_name = env("RUN_NAME")
    run_path = env("RUN_PATH")
    out_path = env("OUT_PATH")
    tmp_path = env("TMP_PATH") or "/tmp"

    if not run_name or not run_path or not out_path:
        log("ERROR", "Missing RUN_NAME/RUN_PATH/OUT_PATH in environment")
        return 0  # do not fail whole container

    os.makedirs(out_path, exist_ok=True)
    os.makedirs(tmp_path, exist_ok=True)

    files = list(iter_files(run_path))
    if not files:
        log("INFO", f"No eligible inputs under: {run_path}")
        return 0

    # single-doc => CSV named after document; multi-doc => CSV named after run
    if len(files) == 1:
        stem = os.path.splitext(os.path.basename(files[0]))[0]
        csv_file = os.path.join(out_path, f"{stem}.csv")
    else:
        csv_file = os.path.join(out_path, f"{run_name}.csv")

    _ensure_csv_header(csv_file)

    for f in files:
        base = os.path.basename(f)
        ext = os.path.splitext(base)[1].lower()

        # Always move these to Mandatory Review
        if ext in REVIEW_EXT:
            log("INFO", f"Moved to Mandatory Review: {base} — reason: Excel not supported")
            _to_manual(f, out_path, "Excel not supported")
            continue

        # Process supported types via their pass script
        cmd = SUPPORTED_EXT.get(ext)
        if not cmd:
            log("INFO", f"Moved to Mandatory Review: {base} — reason: type not supported")
            _to_manual(f, out_path, "Unsupported type")
            continue

        json_out = os.devnull
        rc = _run(["/app/scripts/" + cmd, f, csv_file, json_out, out_path])

        if rc == 0:
            # success → delete input
            try:
                os.remove(f)
            except Exception:
                pass
        else:
            # any non-zero → Mandatory Review
            log("INFO", f"Moved to Mandatory Review: {base} — reason: pass rc={rc}")
            _to_manual(f, out_path, f"pass rc={rc}")

    # remove leftovers if the run dir is now empty
    _prune_empty_dirs(run_path)
    return 0

def _run(argv):
    try:
        return subprocess.call(argv)
    except Exception:
        return 1

def _ensure_csv_header(path: str):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            import csv
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow(["filename", "page", "text", "method", "used_ocr", "reliability"])

def _to_manual(src: str, out_dir: str, reason: str):
    mr = os.path.join(out_dir, "Mandatory Review")
    os.makedirs(mr, exist_ok=True)
    dst = os.path.join(mr, os.path.basename(src))
    try:
        try:
            os.replace(src, dst)
        except OSError:
            shutil.copy2(src, dst)
            try:
                os.remove(src)
            except Exception:
                pass
    finally:
        man = os.path.join(out_dir, "review_manifest.csv")
        import csv
        with open(man, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow([os.path.basename(src), reason])

def _prune_empty_dirs(root: str):
    # Walk bottom-up and rmdir empties. Never touch non-empty parents.
    for dp, _, _ in os.walk(root, topdown=False):
        if os.path.basename(dp).startswith("."):
            continue
        try:
            if not os.listdir(dp):
                os.rmdir(dp)
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(main())
