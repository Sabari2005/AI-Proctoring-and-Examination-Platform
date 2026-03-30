FROM golang:1.22-alpine

RUN (apk del --no-network wget curl || true) \
    && rm -rf /var/cache/apk/*

RUN mkdir /sandbox && chown 1000:1000 /sandbox

USER 1000:1000
WORKDIR /sandbox
