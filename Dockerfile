FROM python:3.11-slim

# System libraries required by WeasyPrint (Cairo / Pango rendering stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        libffi8 \
        shared-mime-info \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source so this layer is cached
# unless requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The application hard-codes /opt/DMTClearinghouse/ in two places:
#   1. sys.path.append("/opt/DMTClearinghouse/") in dmtclearinghouse.py
#   2. open('/opt/DMTClearinghouse/extras/countries.json', ...)
# A symlink resolves both without touching the main source file.
# These paths should be made relative in a future cleanup pass.
RUN ln -s /app /opt/DMTClearinghouse

EXPOSE 5000

# 2 sync workers is sufficient for a low-concurrency internal service;
# increase --workers or switch to --worker-class gevent for higher load.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "dmtclearinghouse:app"]
