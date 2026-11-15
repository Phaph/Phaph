# PoE 2 build optimizer: API + headless Path of Building engine.

# Stage 1: build PoB + LuaJIT + lua-utf8. The full Python image already has git, make and gcc.
FROM python:3.12 AS build
WORKDIR /app
# Empty = the PoB commit pinned in setup.sh. Staging passes another one to try a new PoB (LAUNCH_1.0.md).
ARG POB_REF=
COPY engine/setup.sh engine/setup.sh
RUN engine/setup.sh \
 && rm -rf engine/vendor/LuaJIT/.git engine/vendor/luautf8 engine/vendor/PathOfBuilding-PoE2/.git

# Stage 2: slim runtime.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=build /app/engine/vendor engine/vendor
COPY engine engine
COPY api api

ENV JOBS_DB=/data/jobs.sqlite3 \
    JOB_WORKERS=1
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
