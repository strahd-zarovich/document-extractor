#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_summary.py

v0.1.9 helper for run-level summary reporting.

Purpose:
- track high-level run counts
- keep process_run.py from becoming a counter/reporting script
- provide a simple end-of-run summary in run.log
- support future run_summary.json output

This module should not process, move, delete, or extract files.
It only counts and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Optional


@dataclass
class RunSummary:
    run_name: str = ""

    files_seen: int = 0
    files_processed: int = 0
    files_accepted: int = 0
    files_deleted_success: int = 0

    files_manual_review: int = 0
    files_unsupported: int = 0
    files_ignored: int = 0
    files_noise_deleted: int = 0

    pass_failures: int = 0
    missing_pass_scripts: int = 0

    cleanup_empty_dirs_removed: int = 0
    cleanup_portfolio_stash_removed: int = 0
    cleanup_portfolio_stash_kept_debug: int = 0

    def inc(self, field: str, amount: int = 1) -> None:
        """
        Increment a counter by name.
        Safe no-op if the field does not exist.
        """
        if hasattr(self, field):
            setattr(self, field, int(getattr(self, field)) + int(amount))

    def to_dict(self) -> dict:
        return asdict(self)


def log_summary(summary: RunSummary, logger=None) -> None:
    """
    Write a readable summary to the run log.
    """
    lines = [
        "========== RUN SUMMARY ==========",
        f"Run: {summary.run_name}",
        f"Files seen: {summary.files_seen}",
        f"Files processed: {summary.files_processed}",
        f"Files accepted: {summary.files_accepted}",
        f"Files deleted after success: {summary.files_deleted_success}",
        f"Files moved to Manual Review: {summary.files_manual_review}",
        f"Unsupported files: {summary.files_unsupported}",
        f"Ignored files: {summary.files_ignored}",
        f"Noise files deleted: {summary.files_noise_deleted}",
        f"Pass failures: {summary.pass_failures}",
        f"Missing pass scripts: {summary.missing_pass_scripts}",
        f"Empty dirs removed: {summary.cleanup_empty_dirs_removed}",
        f"Portfolio stash removed: {summary.cleanup_portfolio_stash_removed}",
        f"Portfolio stash kept for debug: {summary.cleanup_portfolio_stash_kept_debug}",
        "=================================",
    ]

    for line in lines:
        if logger:
            logger.info(line)
        else:
            print(line)


def write_summary_json(summary: RunSummary, out_dir: str | Path) -> Path:
    """
    Write run_summary.json.

    This is useful for later WebUI or automated comparison.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "run_summary.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, indent=2)

    try:
        path.chmod(0o664)
    except Exception:
        pass

    return path


if __name__ == "__main__":
    s = RunSummary(run_name="test")
    s.inc("files_seen")
    s.inc("files_accepted")
    log_summary(s)