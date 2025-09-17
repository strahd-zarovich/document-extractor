#!/usr/bin/env python3
import argparse, os, re, shlex, subprocess, sys, csv, time, shutil
from pathlib import Path

def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}] {msg}", flush=True)

def is_hidden(p: Path) -> bool:
    return p.name.startswith(".")

def run_cmd(cmd, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def list_attachments(pdf: Path) -> int:
    # pdfdetach -list returns lines like: "1: name: foo.pdf ..."
    res = run_cmd(["pdfdetach", "-list", str(pdf)])
    if res.returncode != 0:
        return 0
    count = 0
    for line in res.stdout.splitlines():
        if re.match(r"^\s*\d+:", line):
            count += 1
    return count

def ensure_modes(target: Path, puid: int, pgid: int):
    try:
        os.chown(target, puid, pgid)
    except Exception:
        pass
    try:
        if target.is_dir():
            target.chmod(0o775)
        else:
            target.chmod(0o664)
    except Exception:
        pass

def space_ok(dir_path: Path, min_bytes: int = 1_000_000_000) -> bool:
    try:
        st = os.statvfs(str(dir_path))
        free = st.f_bavail * st.f_frsize
        return free >= min_bytes
    except Exception:
        return True  # if we can't tell, don't block

def write_manifest(folder: Path, parent_pdf: Path, children: list[Path]):
    mf = folder / "portfolio_manifest.csv"
    with mf.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["parent_pdf","child_name","child_relpath","size_bytes"])
        for c in children:
            try:
                size = c.stat().st_size
            except Exception:
                size = ""
            w.writerow([parent_pdf.name, c.name, str(c.relative_to(folder)), size])
    return mf

def hide_or_move_parent_to_workdir(parent_pdf: Path, input_root: Path, work_dir: Path, puid: int, pgid: int) -> bool:
    """
    Move the parent portfolio into WORK_DIR/portfolio_hidden/<relpath>/.Parent.pdf
    Fallback to in-place .rename if moving fails.
    """
    try:
        parent_pdf = parent_pdf.resolve()
        input_root = input_root.resolve()
        work_dir = work_dir.resolve()

        # Mirror the run's relative path under WORK_DIR/portfolio_hidden/
        rel_dir = os.path.relpath(parent_pdf.parent, input_root)
        hidden_root = work_dir / "portfolio_hidden" / rel_dir
        hidden_root.mkdir(parents=True, exist_ok=True)
        ensure_modes(hidden_root, puid, pgid)

        dest_path = hidden_root / f".{parent_pdf.name}"
        shutil.move(str(parent_pdf), str(dest_path))
        ensure_modes(dest_path, puid, pgid)
        log(f"Parent moved to tmp: {dest_path}")
        return True
    except Exception as e:
        # Fallback: old behavior—rename to .Parent.pdf in-place
        try:
            hidden_parent = parent_pdf.parent / f".{parent_pdf.name}"
            shutil.move(str(parent_pdf), str(hidden_parent))
            ensure_modes(hidden_parent, puid, pgid)
            log(f"Parent hidden in place: {hidden_parent} (fallback due to: {e})")
            return True
        except Exception as e2:
            log(f"WARNING: could not hide/move parent {parent_pdf.name}: {e2}")
            return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Root folder to scan (e.g., /data/input)")
    ap.add_argument("--parent-disposition", choices=["hide","leave"], default="hide",
                    help="What to do with the portfolio parent after extraction")
    ap.add_argument("--puid", type=int, default=99)
    ap.add_argument("--pgid", type=int, default=100)
    ap.add_argument("--umask", default="0002")
    # NEW: allow passing workdir; default to env WORK_DIR or /data/tmp
    ap.add_argument("--workdir", default=os.environ.get("WORK_DIR", "/data/tmp"))
    args = ap.parse_args()

    os.umask(int(args.umask, 8))
    root = Path(args.input).resolve()
    if not root.exists():
        log(f"ERROR: input path does not exist: {root}")
        sys.exit(1)

    work_dir = Path(args.workdir)
    log(f"Scanning for PDF portfolios under: {root}")

    # Walk all PDFs (skip hidden dirs)
    pdfs: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune hidden dirs so we don't descend into them
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.lower().endswith(".pdf"):
                pdfs.append(Path(dirpath) / fn)

    processed = 0
    portfolios = 0
    for pdf in pdfs:
        processed += 1
        try:
            attach_count = list_attachments(pdf)
        except Exception:
            attach_count = 0

        if attach_count <= 0:
            continue

        portfolios += 1
        log(f"PORTFOLIO detected ({attach_count} attachments): {pdf}")

        out_dir = pdf.with_name(f"{pdf.stem}__portfolio")
        out_dir.mkdir(parents=True, exist_ok=True)
        ensure_modes(out_dir, args.puid, args.pgid)

        if not space_ok(out_dir, 1_000_000_000):
            log(f"WARNING: <1GB free where extracting: {out_dir} (skipping {pdf.name})")
            continue

        # Extract all attachments with pdfdetach
        res = run_cmd(["pdfdetach", "-saveall", "-o", str(out_dir), str(pdf)])
        if res.returncode != 0:
            log(f"ERROR: pdfdetach failed for {pdf.name}: {res.stderr.strip()}")
            continue

        # Normalize perms for extracted files
        children = []
        for child in out_dir.iterdir():
            if child.is_file():
                ensure_modes(child, args.puid, args.pgid)
                # Prefix filename with parent for traceability in your CSV
                # e.g., Parent.pdf::Child.pdf
                new_name = f"{pdf.name}::{child.name}"
                new_path = child.with_name(new_name)
                try:
                    child.rename(new_path)
                    child = new_path
                except Exception:
                    pass
                children.append(child)

        # Write manifest
        mf = write_manifest(out_dir, pdf, children)
        ensure_modes(mf, args.puid, args.pgid)

        # Hide/move the parent so your pipeline ignores it
        if args.parent_disposition == "hide":
            hide_or_move_parent_to_workdir(pdf, root, work_dir, args.puid, args.pgid)

        log(f"PORTFOLIO extracted -> {out_dir} ({len(children)} children)")

    log(f"Done. PDFs scanned: {processed}, portfolios: {portfolios}")

if __name__ == "__main__":
    main()
