#!/bin/bash
# build_sandboxes.sh — Build all sandbox Docker images
# Run this once on the Lightning AI machine before starting the platform.

set -e

PREFIX="proctor-sandbox"
DOCKER_DIR="./docker/sandbox"

echo "Building sandbox images..."

docker build -t ${PREFIX}-python:latest   -f ${DOCKER_DIR}/python.Dockerfile   ${DOCKER_DIR}
docker build -t ${PREFIX}-nodejs:latest   -f ${DOCKER_DIR}/nodejs.Dockerfile   ${DOCKER_DIR}
docker build -t ${PREFIX}-java:latest     -f ${DOCKER_DIR}/java.Dockerfile     ${DOCKER_DIR}
docker build -t ${PREFIX}-cpp:latest      -f ${DOCKER_DIR}/cpp.Dockerfile      ${DOCKER_DIR}
docker build -t ${PREFIX}-go:latest       -f ${DOCKER_DIR}/go.Dockerfile       ${DOCKER_DIR}

echo ""
echo "All sandbox images built:"
docker images | grep ${PREFIX}
echo ""
echo "Next: run 'docker compose up -d' to start the platform."
