#!/bin/bash
# =============================================================================
# Multi-platform Docker Image Build Script
# Builds and pushes images for linux/amd64 and linux/arm64
# =============================================================================

set -e

# Configuration
DOCKER_HUB_USER="${DOCKER_HUB_USER:-catface996}"
IMAGE_NAME="${IMAGE_NAME:-hierarchical-agents}"
VERSION="${VERSION:-latest}"

FULL_IMAGE="${DOCKER_HUB_USER}/${IMAGE_NAME}"

echo "=============================================="
echo "Building Multi-platform Docker Image"
echo "=============================================="
echo "Image: ${FULL_IMAGE}"
echo "Version: ${VERSION}"
echo "Platforms: linux/amd64, linux/arm64"
echo "=============================================="

# Ensure buildx builder exists
BUILDER_NAME="multiplatform-builder"
if ! docker buildx inspect ${BUILDER_NAME} > /dev/null 2>&1; then
    echo "Creating buildx builder: ${BUILDER_NAME}"
    docker buildx create --name ${BUILDER_NAME} --driver docker-container --use
else
    echo "Using existing builder: ${BUILDER_NAME}"
    docker buildx use ${BUILDER_NAME}
fi

# Bootstrap the builder
echo "Bootstrapping builder..."
docker buildx inspect --bootstrap > /dev/null 2>&1

# Check Docker Hub login
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo ""
    echo "WARNING: Not logged in to Docker Hub"
    echo "Please run: docker login -u ${DOCKER_HUB_USER}"
    echo ""
    read -p "Press Enter after logging in, or Ctrl+C to cancel..."
fi

# Build and push
echo ""
echo "Building and pushing multi-platform image..."
echo ""

docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t "${FULL_IMAGE}:${VERSION}" \
    -t "${FULL_IMAGE}:latest" \
    --push \
    .

echo ""
echo "=============================================="
echo "Build Complete!"
echo "=============================================="
echo ""
echo "Images pushed:"
echo "  - ${FULL_IMAGE}:${VERSION}"
echo "  - ${FULL_IMAGE}:latest"
echo ""
echo "To pull on different platforms:"
echo "  docker pull ${FULL_IMAGE}:latest"
echo ""
echo "To run:"
echo "  docker run -p 8080:8080 ${FULL_IMAGE}:latest"
echo ""
