FROM debian:stable-slim

ARG VERSION=0.0.0
LABEL version="${VERSION}"

# UnRAID-friendly defaults (can be overridden at runtime)
ENV PUID=99 \
    PGID=100

WORKDIR /app

# Core toolchain + Python libs from Debian (avoid pip/PEP 668)
RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    python3-pip \
    python3-pil \
    python3-docx \
    python3-pdfminer \
    python3-lxml \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    antiword \
    file \
    curl \
    unzip \
    gnupg \
    gosu \
    fonts-dejavu \
    fonts-liberation2 \
    inotify-tools \
    mupdf-tools \
  && rm -rf /var/lib/apt/lists/*

# Packages not available in Debian’s repo → use pip
RUN pip3 install --no-cache-dir --break-system-packages \
    PyMuPDF==1.25.4 \    
    pytesseract==0.3.13

# App files
COPY entrypoint.sh /app/

# Ship a default config INSIDE the image; runtime config will live in /data/config
COPY config.conf /app/defaults/config.conf
COPY scripts/ /app/scripts/

# After copying your app into /app
RUN chmod -R a+rX /app

# Make scripts executable and set initial perms
RUN chmod +x /app/entrypoint.sh && \
    find /app/scripts -type f -exec chmod +x {} \; && \
    chown -R ${PUID}:${PGID} /app

# Single data mount pattern (Option B)
VOLUME ["/data", "/tmp"]

ENTRYPOINT ["/app/entrypoint.sh"]
