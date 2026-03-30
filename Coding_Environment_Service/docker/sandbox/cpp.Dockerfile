FROM gcc:13-bookworm

RUN apt-get update && apt-get remove -y wget curl netcat-openbsd \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /sandbox && chown 1000:1000 /sandbox

USER 1000:1000
WORKDIR /sandbox
