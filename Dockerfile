# PoE 2 build optimizer: API + headless Path of Building engine in one image.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git make gcc libc6-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build PoB + LuaJIT + lua-utf8 into engine/vendor (cached layer unless setup.sh changes).
COPY engine/setup.sh engine/setup.sh
RUN engine/setup.sh

COPY engine engine
COPY api api

ENV JOBS_DB=/data/jobs.sqlite3 \
    JOB_WORKERS=1
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
