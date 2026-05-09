ARG BASE_IMAGE=python:3.12-alpine
FROM ${BASE_IMAGE}

RUN apk add --no-cache uv

COPY . /opt/_ai-contained-base

RUN uv pip install --system --break-system-packages /opt/_ai-contained-base/packages/base/

ENV ADDRESS=0.0.0.0
ENV PORT=8080

VOLUME /ai_contained
WORKDIR /ai_contained

HEALTHCHECK --interval=5s --timeout=3s --start-period=2s --retries=3 \
  CMD ["/usr/local/bin/python3", "-c", "import urllib.request, os; urllib.request.urlopen('http://' + os.environ['ADDRESS'] + ':' + os.environ['PORT'] + '/health')"]

CMD ["/usr/local/bin/ai-contained-server"]
