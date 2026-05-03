#!/usr/bin/env bash
# read_paper.sh — Download and convert an arXiv paper to Markdown for terminal reading
# Usage: read_paper.sh <arxiv_id> [output_file]
#
# Format fallback order: HTML → LaTeX source → PDF (pdftotext)
set -euo pipefail

PAPER_ID="$1"
OUTPUT="${2:-/dev/stdout}"

SAFE_ID="${PAPER_ID//\//_}"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

log() { echo "[arxiv-reader] $*" >&2; }

# ── Step 1: Try HTML ──────────────────────────────────────────────
HTML_FILE="$TEMP_DIR/${SAFE_ID}.html"
arxiv download "$PAPER_ID" -f html -o "$TEMP_DIR" --filename "${SAFE_ID}.html" 2>/dev/null || true
if [[ -s "$HTML_FILE" ]]; then
    log "Downloaded HTML, converting to Markdown..."
    arxiv html2md "$HTML_FILE" -o "$OUTPUT" 2>/dev/null || true
    if [[ -s "$OUTPUT" || "$OUTPUT" == "/dev/stdout" ]]; then
        log "Done (HTML → Markdown)"
        exit 0
    fi
fi

# ── Step 2: Try LaTeX source ──────────────────────────────────────
SRC_FILE="$TEMP_DIR/${SAFE_ID}.tar.gz"
arxiv download "$PAPER_ID" -f src -o "$TEMP_DIR" --filename "${SAFE_ID}.tar.gz" 2>/dev/null || true
if [[ -s "$SRC_FILE" ]]; then
    log "Downloaded LaTeX source, extracting..."
    mkdir -p "$TEMP_DIR/src"
    tar xzf "$SRC_FILE" -C "$TEMP_DIR/src" 2>/dev/null || true

    # Find main tex file — prefer one with \documentclass, fallback to largest .tex
    MAIN_TEX=$(grep -rl '\\documentclass' "$TEMP_DIR/src" -m1 2>/dev/null || true)
    if [[ -z "$MAIN_TEX" ]]; then
        MAIN_TEX=$(find "$TEMP_DIR/src" -name "*.tex" -type f -exec wc -c {} + 2>/dev/null | sort -rn | head -1 | awk '{print $2}')
    fi

    if [[ -n "$MAIN_TEX" && -s "$MAIN_TEX" ]]; then
        log "Found main tex: $(basename "$MAIN_TEX")"
        {
            echo "# LaTeX Source: $PAPER_ID"
            echo ""
            echo "> _This paper has no HTML version. Showing raw LaTeX source._"
            echo ""
            cat "$MAIN_TEX"
        } > "$OUTPUT"
        log "Done (LaTeX source)"
        exit 0
    fi
fi

# ── Step 3: Try PDF + pdftotext ───────────────────────────────────
if command -v pdftotext &>/dev/null; then
    PDF_FILE="$TEMP_DIR/${SAFE_ID}.pdf"
    arxiv download "$PAPER_ID" -f pdf -o "$TEMP_DIR" --filename "${SAFE_ID}.pdf" 2>/dev/null || true
    if [[ -s "$PDF_FILE" ]]; then
        log "Downloaded PDF, extracting text..."
        pdftotext -layout "$PDF_FILE" "$TEMP_DIR/out.txt" 2>/dev/null || true
        if [[ -s "$TEMP_DIR/out.txt" ]]; then
            {
                echo "# PDF Text Extraction: $PAPER_ID"
                echo ""
                echo "> _This paper has no HTML or LaTeX source. Text extracted from PDF (may have formatting issues)._"
                echo ""
                cat "$TEMP_DIR/out.txt"
            } > "$OUTPUT"
            log "Done (PDF text extraction)"
            exit 0
        fi
    fi
fi

log "Error: all download methods failed for $PAPER_ID"
exit 1
