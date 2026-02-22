#!/bin/bash
#
# Publish both book editions as a GitHub release (tagged "latest")
# This keeps the PDFs accessible without committing them to the repo.
#
# Source files (from utils/compile_both_editions.py):
#   - main_beyond_popular_science.pdf   : Executive size (7" × 10")
#   - main_unpopular_science.pdf        : Executive size (7" × 10")
#
# Released files:
#   Beyond Popular Science (public edition):
#     - main.pdf              : BPS trade size (6.14" × 9.21") - default download
#     - main_trade.pdf        : BPS trade size (6.14" × 9.21") - explicit name
#     - main_preview.pdf      : BPS compressed for quick review
#
#   Unpopular Science (Kernel Keys Press edition):
#     - unpopular_science_executive.pdf  : US executive size (7" × 10")
#     - unpopular_science_preview.pdf    : US compressed for quick review
#
#   Shared:
#     - cover_refined.pdf                : Book cover
#     - 00_FrontMatter.pdf .. 51_BackMatter.pdf : Individual chapter PDFs (from US)
#
# Prerequisites:
#   brew install gh qpdf
#   gh auth login
#
# Usage:
#   ./release_pdf.sh

set -e

# ---------------------------------------------------------------------------
# Source files (compiled by utils/compile_both_editions.py)
# ---------------------------------------------------------------------------
BPS_EXECUTIVE="main_beyond_popular_science.pdf"     # Beyond Popular Science, 7×10
US_EXECUTIVE="main_unpopular_science.pdf"           # Unpopular Science, 7×10
COVER_FILE="cover/cover_refined.pdf"

# Intermediate trade-size PDFs (generated here)
BPS_TRADE="main_beyond_popular_science_trade.pdf"
US_TRADE="main_unpopular_science_trade.pdf"

# Release file names — Beyond Popular Science (public edition)
REL_BPS_MAIN="main.pdf"                            # Trade size as default download
REL_BPS_TRADE="main_trade.pdf"                     # Trade size with explicit name
REL_BPS_PREVIEW="main_preview.pdf"                 # Compressed trade

# Release file names — Unpopular Science (Kernel Keys Press edition)
REL_US_EXEC="unpopular_science_executive.pdf"       # Executive size
REL_US_PREVIEW="unpopular_science_preview.pdf"      # Compressed executive

REPO="silverdavi/beyond-popular-science"
TAG="latest"

echo "📚 DUAL-EDITION RELEASE SCRIPT"
echo "==========================================="
echo ""

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
MISSING=0
for f in "$BPS_EXECUTIVE" "$US_EXECUTIVE" "$COVER_FILE"; do
  if [ ! -f "$f" ]; then
    echo "❌ Error: $f not found."
    MISSING=1
  fi
done
if [ "$MISSING" -eq 1 ]; then
  echo ""
  echo "Compile both editions first:"
  echo "   python3 utils/compile_both_editions.py"
  exit 1
fi

if ! command -v gh &> /dev/null; then
  echo "❌ Error: GitHub CLI (gh) is not installed."
  echo "   Install it with: brew install gh"
  exit 1
fi

# ---------------------------------------------------------------------------
# Beyond Popular Science — scale to trade
# ---------------------------------------------------------------------------
echo "📐 BPS: Generating trade size PDF (6.14\" × 9.21\")..."
if [ -f "$BPS_TRADE" ] && [ "$BPS_TRADE" -nt "$BPS_EXECUTIVE" ]; then
  echo "   Trade PDF is up to date."
else
  python3 utils/scale_pdf_to_trade.py "$BPS_EXECUTIVE" "$BPS_TRADE"
fi
if [ ! -f "$BPS_TRADE" ]; then
  echo "❌ Error: Failed to generate BPS trade PDF"
  exit 1
fi

echo ""
echo "🗜️  BPS: Generating preview (compressed trade)..."
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile="$REL_BPS_PREVIEW" "$BPS_TRADE"
echo "   ✓ $(du -h "$REL_BPS_PREVIEW" | cut -f1)"

# ---------------------------------------------------------------------------
# Unpopular Science — preview from executive
# ---------------------------------------------------------------------------
echo ""
echo "🗜️  US: Generating preview (compressed executive)..."
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile="$REL_US_PREVIEW" "$US_EXECUTIVE"
echo "   ✓ $(du -h "$REL_US_PREVIEW" | cut -f1)"

# ---------------------------------------------------------------------------
# Chapter splitting — from Unpopular Science (scale to trade first)
# ---------------------------------------------------------------------------
echo ""
echo "📐 US: Scaling to trade for chapter splitting..."
if [ -f "$US_TRADE" ] && [ "$US_TRADE" -nt "$US_EXECUTIVE" ]; then
  echo "   Trade PDF is up to date."
else
  python3 utils/scale_pdf_to_trade.py "$US_EXECUTIVE" "$US_TRADE"
fi

echo ""
echo "📖 Splitting Unpopular Science into individual chapter PDFs..."
CHAPTERS_DIR="chapters_split"
python3 utils/split_chapters.py "$US_TRADE" -o "$CHAPTERS_DIR"

if [ ! -d "$CHAPTERS_DIR" ]; then
  echo "❌ Error: Chapter splitting failed"
  exit 1
fi

CHAPTER_COUNT=$(ls "$CHAPTERS_DIR"/*.pdf | wc -l | tr -d ' ')
echo "   ✓ $CHAPTER_COUNT chapter PDFs ready"

# ---------------------------------------------------------------------------
# Prepare release copies
# ---------------------------------------------------------------------------
echo ""
echo "📦 Preparing release files..."

cp "$BPS_TRADE" "$REL_BPS_MAIN"
cp "$BPS_TRADE" "$REL_BPS_TRADE"
cp "$US_EXECUTIVE" "$REL_US_EXEC"

echo "   Beyond Popular Science (public):"
echo "     ✓ $REL_BPS_MAIN (trade - default)"
echo "     ✓ $REL_BPS_TRADE (trade - explicit)"
echo "     ✓ $REL_BPS_PREVIEW (compressed)"
echo "   Unpopular Science (Kernel Keys Press):"
echo "     ✓ $REL_US_EXEC (executive)"
echo "     ✓ $REL_US_PREVIEW (compressed)"
echo "   Shared:"
echo "     ✓ $COVER_FILE"
echo "     ✓ $CHAPTER_COUNT individual chapter PDFs (from US)"

# ---------------------------------------------------------------------------
# Upload to GitHub
# ---------------------------------------------------------------------------
echo ""
echo "🗑️  Removing old release (if exists)..."
gh release delete "$TAG" -R "$REPO" -y 2>/dev/null || true
git push origin --delete "$TAG" 2>/dev/null || true

echo ""
echo "🚀 Creating new release..."
gh release create "$TAG" \
  "$REL_BPS_MAIN" \
  "$REL_BPS_TRADE" \
  "$REL_BPS_PREVIEW" \
  "$REL_US_EXEC" \
  "$REL_US_PREVIEW" \
  "$COVER_FILE" \
  "$CHAPTERS_DIR"/*.pdf \
  -R "$REPO" \
  --title "Beyond Popular Science / Unpopular Science - Version 1.05" \
  --notes "Automatically updated on $(date '+%Y-%m-%d %H:%M:%S %Z')

## Available Downloads

### Beyond Popular Science (public edition)

#### Trade Size (6.14\" × 9.21\") — Recommended
\`\`\`bash
curl -L -o BeyondPopularScience.pdf https://github.com/$REPO/releases/download/$TAG/main.pdf
\`\`\`

#### Preview (Compressed)
\`\`\`bash
curl -L -o BeyondPopularScience_Preview.pdf https://github.com/$REPO/releases/download/$TAG/main_preview.pdf
\`\`\`

---

### Unpopular Science (Kernel Keys Press edition)

#### Executive Size (7\" × 10\")
\`\`\`bash
curl -L -o UnpopularScience.pdf https://github.com/$REPO/releases/download/$TAG/unpopular_science_executive.pdf
\`\`\`

#### Preview (Compressed)
\`\`\`bash
curl -L -o UnpopularScience_Preview.pdf https://github.com/$REPO/releases/download/$TAG/unpopular_science_preview.pdf
\`\`\`

---

### Individual Chapters (from Unpopular Science)
52 separate PDFs: front matter, 50 chapters (9 pages each), and back matter.
Each chapter can be downloaded individually from the assets list below.

### Cover
\`\`\`bash
curl -L -o Cover.pdf https://github.com/$REPO/releases/download/$TAG/cover_refined.pdf
\`\`\`

Or visit: https://github.com/$REPO/releases/tag/$TAG"

# ---------------------------------------------------------------------------
# Cleanup temporary release copies (keep trade/executive locally)
# ---------------------------------------------------------------------------
rm -f "$REL_BPS_MAIN" "$REL_BPS_PREVIEW" "$REL_US_PREVIEW"
rm -rf "$CHAPTERS_DIR"

echo ""
echo "✅ SUCCESS! Your PDFs are now available:"
echo ""
echo "📖 Beyond Popular Science (trade 6.14\" × 9.21\"):"
echo "   https://github.com/$REPO/releases/download/$TAG/main.pdf"
echo "   https://github.com/$REPO/releases/download/$TAG/main_trade.pdf"
echo "   https://github.com/$REPO/releases/download/$TAG/main_preview.pdf"
echo ""
echo "📖 Unpopular Science (executive 7\" × 10\"):"
echo "   https://github.com/$REPO/releases/download/$TAG/unpopular_science_executive.pdf"
echo "   https://github.com/$REPO/releases/download/$TAG/unpopular_science_preview.pdf"
echo ""
echo "📖 Individual Chapters (from Unpopular Science):"
echo "   52 PDFs available on the release page"
echo ""
echo "🎨 Cover:"
echo "   https://github.com/$REPO/releases/download/$TAG/cover_refined.pdf"
echo ""
echo "Direct download commands:"
echo "   curl -L -o BeyondPopularScience.pdf https://github.com/$REPO/releases/download/$TAG/main.pdf"
echo "   curl -L -o UnpopularScience.pdf https://github.com/$REPO/releases/download/$TAG/unpopular_science_executive.pdf"
echo "   curl -L -o Cover.pdf https://github.com/$REPO/releases/download/$TAG/cover_refined.pdf"
