FROM python@sha256:cae66f2ef0ec51a9891263eeee7f987dacf0a9879e8aa9353d5606e0530619a5
ARG GRADER_SOURCE_SHA=unknown
ARG ENVIRONMENT_SHA256=unknown
LABEL org.dpe.grader_source_sha=$GRADER_SOURCE_SHA
LABEL org.dpe.environment_sha256=$ENVIRONMENT_SHA256
WORKDIR /grader
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 grader \
    && mkdir -p /in /work \
    && chown 1000:1000 /in /work
COPY requirements.lock .python-version contracts.py catalog.py checkouts.py patches.py grader.py docker/entrypoint.sh ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock \
    && chmod 755 /grader/entrypoint.sh
USER 1000:1000
ENTRYPOINT ["/grader/entrypoint.sh"]
