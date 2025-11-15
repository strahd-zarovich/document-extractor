#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import uuid

def convert_to_pdf(doc_path: str, logger=None) -> str:
    """
    Convert .doc or .docx to PDF using LibreOffice or unoconv.
    Returns path to generated PDF or None on failure.
    """

    workdir = "/tmp/work"
    os.makedirs(workdir, exist_ok=True)

    # output: random unique name to avoid collisions
    pdf_out = os.path.join(workdir, f"fallback_{uuid.uuid4().hex}.pdf")

    if logger:
        logger.info(f"Fallback DOC→PDF: {os.path.basename(doc_path)} → {pdf_out}")

    # Option A — LibreOffice (preferred)
    try:
        cmd = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", workdir, doc_path]
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # LibreOffice generates filename automatically
        guessed_pdf = os.path.join(workdir, os.path.splitext(os.path.basename(doc_path))[0] + ".pdf")
        if os.path.exists(guessed_pdf):
            os.rename(guessed_pdf, pdf_out)
            return pdf_out
    except Exception:
        pass

    # Option B — unoconv
    try:
        cmd = ["unoconv", "-f", "pdf", "-o", pdf_out, doc_path]
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(pdf_out):
            return pdf_out
    except Exception:
        pass

    if logger:
        logger.error("DOC→PDF conversion failed (LibreOffice/unoconv not available).")

    return None
