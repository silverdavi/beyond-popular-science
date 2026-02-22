#!/bin/bash
# Activate the Python virtual environment for this project

echo "Activating Python virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated!"
echo "You can now run Python scripts with all dependencies available."
echo ""
echo "To deactivate, run: deactivate"
echo ""
echo "Available utility scripts:"
echo "  python utils/analyze_chapter_pages.py"
echo "  python utils/analyze_chapters.py"
echo "  python utils/compile_incremental.py"
echo "  python utils/compile_realtime.py"
echo "  python utils/llm_editor/cli.py" 