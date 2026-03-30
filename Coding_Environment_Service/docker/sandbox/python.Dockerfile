# Minimal Python sandbox - NO shell, NO network tools, NO package managers
FROM python:3.11-slim-bookworm

# Remove all non-essential tools that could be exploited
RUN apt-get update && apt-get remove -y \
    wget curl netcat-openbsd nmap \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /usr/bin/wget /usr/bin/curl

# Create sandbox working dir
RUN mkdir /sandbox && chown 1000:1000 /sandbox

# Pre-install nothing extra — candidates use stdlib only
# (Customize per exam: RUN pip install --no-cache-dir numpy pandas)

USER 1000:1000
WORKDIR /sandbox

# No ENTRYPOINT — command is passed at runtime by SandboxExecutor
