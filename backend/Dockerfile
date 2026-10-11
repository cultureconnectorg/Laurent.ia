# syntax=docker/dockerfile:1.7
# Laurent.ia backend — self-hosted image (G1). No external provider, no Emergent package.
FROM ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates curl \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY requirements.txt .
# emergentintegrations is not on PyPI and not needed by the sovereign engine path (S2).
# Optional build secret `extra_ca`: only for a TLS-intercepting proxy at build time;
# never copied into the image. Unused on a normal network.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi \
 && grep -vE '^emergentintegrations' requirements.txt > /tmp/req.txt \
 && pip install --no-cache-dir -r /tmp/req.txt
COPY . .
RUN useradd --system --uid 10001 laurentia && chown -R laurentia /app
USER laurentia
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD curl -sf http://127.0.0.1:8001/api/health || exit 1
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
