FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/* \
 && npm install -g squawk-cli@1 >/dev/null 2>&1 || true
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /work
ENV PYTHONUNBUFFERED=1 RB_DB_HOST=db RB_DB_PORT=5432
