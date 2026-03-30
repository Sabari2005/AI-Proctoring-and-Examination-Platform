FROM node:20-slim

RUN apt-get update && apt-get remove -y wget curl \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /sandbox && chown 1000:1000 /sandbox

USER 1000:1000
WORKDIR /sandbox
