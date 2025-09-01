FROM debian:stable-slim

# UnRAID-friendly defaults (can be overridden at runtime)
ENV PUID=99 \
    PGID=100

WORKDIR /app

# Core toolchain + Python libs from Debian (avoid pip/PEP 668)
RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    python3-pip \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    mupdf-tools \
    libreoffice \
    ocrmypdf \
    imagemagick \
    libimage-exiftool-perl \
    ghostscript \
    docx2txt \
    jq \
    file \
    python3-lxml \
    python3-docx \
    python3-pdfminer \
  && rm -rf /var/lib/apt/lists/*

# App files
COPY entrypoint.sh /app/
# Ship a default config INSIDE the image; runtime config will live in /data/config
COPY config.conf /app/defaults/config.conf
COPY scripts/ /app/scripts/

# Make scripts executable and set initial perms
RUN chmod +x /app/entrypoint.sh && \
    find /app/scripts -type f -exec chmod +x {} \; && \
    chown -R ${PUID}:${PGID} /app

# Single data mount pattern (Option B)
VOLUME ["/data", "/tmp"]

ENTRYPOINT ["/app/entrypoint.sh"]
