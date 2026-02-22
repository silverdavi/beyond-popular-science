#!/usr/bin/env python3
"""
Generate a table of contents by extracting titles and summaries from all chapters.
"""

import os
import re
from pathlib import Path

def clean_latex_text(text):
    """Remove LaTeX commands and clean up text for plain text output."""
    # Remove common LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)  # \command{text} -> text
    text = re.sub(r'\\[a-zA-Z]+', '', text)  # Remove \command
    text = re.sub(r'\{|\}', '', text)  # Remove braces
    text = re.sub(r'\$([^$]*)\$', r'\1', text)  # Remove $ math delimiters
    text = re.sub(r'\\[()\[\]]', '', text)  # Remove \( \) \[ \]
    text = re.sub(r'\\', '', text)  # Remove remaining backslashes
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()

def read_chapter_file(chapter_dir, filename):
    """Read and clean content from a chapter file."""
    file_path = chapter_dir / filename
    if not file_path.exists():
        return ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean the content
        content = clean_latex_text(content)
        return content
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return ""

def main():
    workspace_dir = Path(".")
    
    # Get all chapter directories and sort them numerically
    chapter_dirs = []
    for item in workspace_dir.iterdir():
        if item.is_dir() and re.match(r'^\d+_', item.name):
            # Extract chapter number for sorting
            match = re.match(r'^(\d+)_', item.name)
            if match:
                chapter_num = int(match.group(1))
                chapter_dirs.append((chapter_num, item))
    
    # Sort by chapter number
    chapter_dirs.sort(key=lambda x: x[0])
    
    toc_content = []
    toc_content.append("TABLE OF CONTENTS")
    toc_content.append("=================")
    toc_content.append("")
    toc_content.append("UNPOPULAR SCIENCE: A Collection of Mathematical and Scientific Essays")
    toc_content.append("")
    
    for chapter_num, chapter_dir in chapter_dirs:
        print(f"Processing Chapter {chapter_num}: {chapter_dir.name}")
        
        # Read title
        title = read_chapter_file(chapter_dir, "title.tex")
        
        # Read summary
        summary = read_chapter_file(chapter_dir, "summary.tex")
        
        # Format chapter entry
        toc_content.append(f"Chapter {chapter_num:02d}: {title}")
        toc_content.append("-" * (len(f"Chapter {chapter_num:02d}: {title}")))
        
        if summary:
            # Wrap long summaries nicely
            words = summary.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line + " " + word) <= 80:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                toc_content.append(line)
        else:
            toc_content.append("(Summary not available)")
        
        toc_content.append("")
    
    # Write to file
    output_file = "TABLE_OF_CONTENTS.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(toc_content))
    
    print(f"\n✅ Table of Contents generated: {output_file}")
    print(f"📄 {len(chapter_dirs)} chapters processed")
    print(f"📝 {len(toc_content)} lines written")

if __name__ == "__main__":
    main()