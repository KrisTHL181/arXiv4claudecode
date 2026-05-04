#!/usr/bin/env bash
# install_ar5ivist.sh — Install ar5ivist (LaTeX → HTML converter for arXiv papers)
#
# Tries these strategies in order:
#   1. Docker pull of pre-built latexml/ar5ivist image
#   2. Local Docker build from the ar5ivist GitHub repo
#   3. Print manual install instructions
#
# Usage: bash scripts/install_ar5ivist.sh

set -euo pipefail

AR5IVIST_IMAGE="latexml/ar5ivist:2512.17"
AR5IVIST_REPO="https://github.com/dginev/ar5ivist.git"

log() { echo "[install-ar5ivist] $*" >&2; }

log "Checking for ar5ivist installation options..."

# ── Strategy 1: Docker pull ──────────────────────────────────
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    log "Docker found and running. Pulling ar5ivist image..."
    if docker pull "$AR5IVIST_IMAGE" 2>/dev/null; then
        if docker image inspect "$AR5IVIST_IMAGE" &>/dev/null; then
            log "Success: ar5ivist Docker image installed."
            log "Installation complete."
            exit 0
        fi
    fi

    # ── Strategy 2: Build from source ────────────────────────
    log "Docker pull failed. Attempting to build from source..."
    BUILD_DIR=$(mktemp -d)
    trap 'rm -rf "$BUILD_DIR"' EXIT

    if git clone --depth=1 "$AR5IVIST_REPO" "$BUILD_DIR" 2>/dev/null; then
        if [[ -f "$BUILD_DIR/ar5ivist-base/Dockerfile" ]]; then
            log "Building ar5ivist-base image..."
            docker build -t latexml/ar5ivist-base "$BUILD_DIR/ar5ivist-base" 2>/dev/null || true
        fi
        if [[ -f "$BUILD_DIR/ar5ivist/Dockerfile" ]]; then
            log "Building ar5ivist image..."
            docker build -t "$AR5IVIST_IMAGE" "$BUILD_DIR/ar5ivist" 2>/dev/null || true
        fi

        if docker image inspect "$AR5IVIST_IMAGE" &>/dev/null; then
            log "Success: ar5ivist Docker image built from source."
            log "Installation complete."
            exit 0
        fi
    fi
    log "Docker build failed."
else
    log "Docker not found or not running."
fi

# ── Strategy 3: Manual instructions ──────────────────────────
cat >&2 <<EOF

ar5ivist could not be installed automatically.

The arXiv CLI will fall back to raw LaTeX output when HTML is unavailable.

To install manually:
  1. Install Docker from https://docs.docker.com/get-docker/
  2. Run: docker pull $AR5IVIST_IMAGE
  3. Verify: docker image inspect $AR5IVIST_IMAGE

Alternatively, install latexml locally:
  - Ubuntu/Debian: sudo apt install latexml
  - macOS: brew install latexml
  - Or: cpan install LaTeXML
EOF

exit 1
