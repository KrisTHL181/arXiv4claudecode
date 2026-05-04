#!/usr/bin/env bash
# read_paper.sh — Download and convert an arXiv paper to Markdown
# Usage: read_paper.sh <arxiv_id> [output_file]
#
# Conversion fallback order (handled internally by arxiv html2md):
#   1. arXiv native HTML
#   2. ar5ivist (Docker or local LaTeX→HTML)
#   3. Raw LaTeX source
#
# Additionally falls back to PDF text extraction as last resort.
#
# Examples:
#   read_paper.sh 2107.05580
#   read_paper.sh 2107.05580 paper.md
#   read_paper.sh math/0211159

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: read_paper.sh <arxiv_id> [output_file]" >&2
    exit 1
fi

PAPER_ID="$1"
OUTPUT="${2:-/dev/stdout}"

log() { echo "[arxiv-reader] $*" >&2; }

# ── Step 1: Use arxiv html2md (handles HTML → ar5ivist → LaTeX) ──
log "Converting paper $PAPER_ID..."
if arxiv html2md "$PAPER_ID" -o "$OUTPUT" 2>/dev/null; then
    if [[ -s "$OUTPUT" || "$OUTPUT" == "/dev/stdout" ]]; then
        log "Done."
        exit 0
    fi
fi

# ── Step 2: Last resort — PDF text extraction ──────────────────
SAFE_ID="${PAPER_ID//\//_}"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

if command -v pdftotext &>/dev/null; then
    PDF_FILE="$TEMP_DIR/${SAFE_ID}.pdf"
    arxiv download "$PAPER_ID" -f pdf -o "$TEMP_DIR" --filename "${SAFE_ID}.pdf" 2>/dev/null || true
    if [[ -s "$PDF_FILE" ]]; then
        log "Extracting text from PDF..."
        pdftotext -layout "$PDF_FILE" "$TEMP_DIR/out.txt" 2>/dev/null || true
        if [[ -s "$TEMP_DIR/out.txt" ]]; then
            {
                echo "# PDF Text Extraction: $PAPER_ID"
                echo ""
                echo "> _All other formats unavailable. Text extracted from PDF (may have formatting issues)._"
                echo ""
                cat "$TEMP_DIR/out.txt"
            } > "$OUTPUT"
            log "Done (PDF text extraction)."
            exit 0
        fi
    fi
fi

log "Error: all methods failed for $PAPER_ID"
exit 1
