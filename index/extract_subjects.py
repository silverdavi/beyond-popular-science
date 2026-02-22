#!/usr/bin/env python3
"""
Two-Pass Subject Index Extraction using Gemini 3 Pro Preview.

Pass 1: Extract candidate subjects/subtopics from all 50 chapters (parallel)
        Output: candidates.json for manual review

Pass 2: After review, classify each chapter using ONLY approved subjects
        Input: approved_subjects.json (edited from candidates)
        Output: final_index.json and subject_index_new.tex

Usage:
    python extract_subjects.py pass1          # Extract candidates
    python extract_subjects.py pass2          # Classify with approved list
    python extract_subjects.py --help         # Show help
"""

import os
import sys
import json
import asyncio
import re
from pathlib import Path
from datetime import datetime
import time

# Configuration - NO FALLBACK, use exact model
MODEL_NAME = "gemini-3-pro-preview"  # As specified - no fallback to 2.5 or 2.0
OUTPUT_DIR = Path(__file__).parent


def load_env():
    """Load .env file."""
    env_paths = [
        Path(__file__).parent.parent / '.env',
        Path.cwd() / '.env',
        Path.home() / '.env',
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        k, v = line.strip().split('=', 1)
                        os.environ[k] = v.strip().strip('"').strip("'")
            break


def get_api_key():
    """Get Gemini API key."""
    load_env()
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        print("ERROR: No Gemini API key found in .env!")
        sys.exit(1)
    return key


def read_chapter_content(chapter_dir: Path) -> str:
    """Read all content files from a chapter directory."""
    content_parts = []
    files = ['title.tex', 'summary.tex', 'historical.tex', 'main.tex', 'technical.tex']
    
    for filename in files:
        filepath = chapter_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                # Clean LaTeX but keep readable text
                text = re.sub(r'\\begin\{[^}]+\}', '', text)
                text = re.sub(r'\\end\{[^}]+\}', '', text)
                text = re.sub(r'\\[a-zA-Z]+\*?\{([^}]*)\}', r'\1', text)
                text = re.sub(r'\\[a-zA-Z]+\[[^\]]*\]', '', text)
                text = re.sub(r'\\[a-zA-Z]+', ' ', text)
                text = re.sub(r'[{}]', '', text)
                text = re.sub(r'\$[^$]+\$', '[math]', text)
                text = re.sub(r'\s+', ' ', text)
                content_parts.append(f"=== {filename.upper()} ===\n{text.strip()}")
    
    return '\n\n'.join(content_parts)


def get_chapter_directories() -> list:
    """Get all chapter directories in order."""
    project_root = Path(__file__).parent.parent
    chapters = []
    for d in sorted(project_root.iterdir()):
        if d.is_dir() and re.match(r'^\d{2}_', d.name):
            chapters.append(d)
    return chapters


# ============================================================================
# PASS 1: Extract Candidates
# ============================================================================

PASS1_PROMPT = """You are a professional book indexer creating a detailed subject index.

Analyze this chapter and extract ALL significant subjects and concepts that a reader might look up. For each subject, identify relevant subtopics within this chapter.

Return a JSON object with this structure:
{{
  "subjects": [
    {{"subject": "Main Subject", "subtopics": ["subtopic1", "subtopic2"]}},
    {{"subject": "Another Subject", "subtopics": []}},
    ...
  ]
}}

Guidelines:
1. Extract 20-50 entries per chapter depending on content density
2. Include: scientific concepts, mathematical terms, historical figures, phenomena, theories, techniques, named effects/laws, applications
3. Use hierarchical structure: broad subjects with specific subtopics
4. Examples:
   - {{"subject": "Quantum mechanics", "subtopics": ["tunneling", "wave function", "uncertainty"]}}
   - {{"subject": "Relativity", "subtopics": ["time dilation", "length contraction"]}}
   - {{"subject": "Set theory", "subtopics": ["axiom of choice", "non-measurable sets"]}}
5. Keep subject names concise (1-4 words)
6. Include people's names as subjects when they're discussed significantly
7. Do NOT include: chapter titles, generic terms like "introduction"

CHAPTER CONTENT:
{chapter_content}

Return ONLY valid JSON, no markdown formatting.
"""


async def extract_candidates_for_chapter(chapter_dir: Path, chapter_num: int, model) -> dict:
    """Pass 1: Extract candidate subjects from a single chapter."""
    chapter_name = chapter_dir.name
    
    try:
        content = read_chapter_content(chapter_dir)
        if len(content) > 40000:
            content = content[:40000] + "\n\n[Content truncated...]"
        
        prompt = PASS1_PROMPT.format(chapter_content=content)
        
        # Use async for parallel execution
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        
        response_text = response.text.strip()
        
        # Clean up response
        if response_text.startswith('```'):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        data = json.loads(response_text)
        subjects = data.get('subjects', [])
        
        print(f"  ✓ Ch.{chapter_num:02d} {chapter_name[:30]}: {len(subjects)} subjects")
        
        return {
            'chapter_num': chapter_num,
            'chapter_dir': chapter_name,
            'subjects': subjects,
            'error': None
        }
        
    except Exception as e:
        print(f"  ✗ Ch.{chapter_num:02d} {chapter_name[:30]}: ERROR - {e}")
        return {
            'chapter_num': chapter_num,
            'chapter_dir': chapter_name,
            'subjects': [],
            'error': str(e)
        }


async def run_pass1():
    """Pass 1: Extract all candidate subjects in parallel."""
    print("=" * 70)
    print("PASS 1: EXTRACTING CANDIDATE SUBJECTS")
    print(f"Model: {MODEL_NAME} (NO FALLBACK)")
    print("=" * 70)
    
    # Initialize Gemini
    import google.generativeai as genai
    api_key = get_api_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    
    chapters = get_chapter_directories()
    print(f"\n📖 Processing {len(chapters)} chapters in parallel...\n")
    
    start_time = time.time()
    
    # Run ALL 50 in parallel
    tasks = [
        extract_candidates_for_chapter(chapter_dir, i, model)
        for i, chapter_dir in enumerate(chapters, 1)
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Completed in {elapsed:.1f}s")
    
    # Sort by chapter number
    results.sort(key=lambda x: x['chapter_num'])
    
    # Save raw results
    raw_output = OUTPUT_DIR / 'pass1_raw_results.json'
    with open(raw_output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Raw results saved: {raw_output}")
    
    # Consolidate all unique subjects
    all_subjects = {}  # subject -> set of subtopics
    
    for result in results:
        for entry in result.get('subjects', []):
            subj = entry.get('subject', '').strip()
            if not subj:
                continue
            
            # Normalize
            subj_key = subj.lower()
            if subj_key not in all_subjects:
                all_subjects[subj_key] = {'display': subj, 'subtopics': set()}
            
            for subtopic in entry.get('subtopics', []):
                if subtopic:
                    all_subjects[subj_key]['subtopics'].add(subtopic.lower().strip())
    
    # Create candidates file for review
    candidates = []
    for subj_key in sorted(all_subjects.keys()):
        data = all_subjects[subj_key]
        candidates.append({
            'subject': data['display'],
            'subtopics': sorted(list(data['subtopics'])),
            'include': True  # Default to include, user can set to False
        })
    
    candidates_output = OUTPUT_DIR / 'candidates.json'
    with open(candidates_output, 'w') as f:
        json.dump(candidates, f, indent=2)
    
    print(f"✅ Candidates saved: {candidates_output}")
    print(f"\n📊 Summary:")
    print(f"   Total unique subjects: {len(candidates)}")
    print(f"   Chapters with errors: {sum(1 for r in results if r.get('error'))}")
    
    print(f"\n📝 NEXT STEPS:")
    print(f"   1. Review and edit: {candidates_output}")
    print(f"   2. Set 'include': false for subjects to exclude")
    print(f"   3. Rename subjects as needed (keep consistent)")
    print(f"   4. Run: python extract_subjects.py pass2")


# ============================================================================
# PASS 2: Classify with Approved Subjects
# ============================================================================

PASS2_PROMPT = """You are a professional book indexer. Classify this chapter's content using ONLY the approved subjects and subtopics provided.

APPROVED SUBJECTS (use ONLY these exact names):
{approved_subjects_list}

For this chapter, identify which approved subjects and subtopics are discussed. Return a JSON array:
[
  {{"subject": "Exact Subject Name", "subtopic": "exact subtopic" or null}},
  ...
]

Rules:
1. Use ONLY subjects from the approved list - do not invent new ones
2. Use exact spelling from the approved list
3. Include a subject if the chapter discusses it meaningfully (not just mentions)
4. Include subtopics only if specifically discussed
5. Return 10-30 entries per chapter

CHAPTER CONTENT:
{chapter_content}

Return ONLY valid JSON array, no markdown.
"""


async def classify_chapter(chapter_dir: Path, chapter_num: int, model, approved_subjects: str) -> dict:
    """Pass 2: Classify a chapter using only approved subjects."""
    chapter_name = chapter_dir.name
    
    try:
        content = read_chapter_content(chapter_dir)
        if len(content) > 40000:
            content = content[:40000] + "\n\n[Content truncated...]"
        
        prompt = PASS2_PROMPT.format(
            approved_subjects_list=approved_subjects,
            chapter_content=content
        )
        
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        
        response_text = response.text.strip()
        
        if response_text.startswith('```'):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        entries = json.loads(response_text)
        
        return {
            'chapter_num': chapter_num,
            'chapter_dir': chapter_name,
            'entries': entries,
            'error': None
        }
        
    except Exception as e:
        return {
            'chapter_num': chapter_num,
            'chapter_dir': chapter_name,
            'entries': [],
            'error': str(e)
        }


async def run_pass2():
    """Pass 2: Classify all chapters using approved subjects."""
    import sys
    print("=" * 70, flush=True)
    print("PASS 2: CLASSIFYING WITH APPROVED SUBJECTS", flush=True)
    print(f"Model: {MODEL_NAME} (NO FALLBACK)", flush=True)
    print("=" * 70, flush=True)
    sys.stdout.flush()
    
    # Load approved subjects
    candidates_file = OUTPUT_DIR / 'candidates.json'
    if not candidates_file.exists():
        print(f"\n❌ ERROR: {candidates_file} not found!", flush=True)
        print("   Run pass1 first: python extract_subjects.py pass1", flush=True)
        sys.exit(1)
    
    with open(candidates_file) as f:
        candidates = json.load(f)
    
    # Filter to included subjects only
    approved = [c for c in candidates if c.get('include', True)]
    
    if not approved:
        print("\n❌ ERROR: No approved subjects found!", flush=True)
        print("   Edit candidates.json and set 'include': true for subjects to keep", flush=True)
        sys.exit(1)
    
    print(f"\n📋 Using {len(approved)} approved subjects", flush=True)
    
    # Format approved subjects for prompt
    approved_lines = []
    for item in approved:
        subj = item['subject']
        subtopics = item.get('subtopics', [])
        if subtopics:
            approved_lines.append(f"• {subj}: {', '.join(subtopics)}")
        else:
            approved_lines.append(f"• {subj}")
    
    approved_subjects_text = '\n'.join(approved_lines)
    
    # Initialize Gemini
    print("🔌 Initializing Gemini API...", flush=True)
    import google.generativeai as genai
    api_key = get_api_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    print(f"✅ Model ready: {MODEL_NAME}", flush=True)
    
    chapters = get_chapter_directories()
    print(f"\n📖 Processing {len(chapters)} chapters in parallel...", flush=True)
    print(f"🚀 Launching {len(chapters)} async tasks NOW...\n", flush=True)
    sys.stdout.flush()
    
    start_time = time.time()
    completed = [0]  # Use list to allow modification in nested function
    
    async def classify_with_progress(chapter_dir, i, model, approved_text):
        result = await classify_chapter(chapter_dir, i, model, approved_text)
        completed[0] += 1
        print(f"  [{completed[0]:2d}/50] ✓ Ch.{i:02d} {chapter_dir.name[:25]}", flush=True)
        return result
    
    # Run ALL 50 in parallel
    tasks = [
        classify_with_progress(chapter_dir, i, model, approved_subjects_text)
        for i, chapter_dir in enumerate(chapters, 1)
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Completed in {elapsed:.1f}s")
    
    results.sort(key=lambda x: x['chapter_num'])
    
    # Save raw results
    raw_output = OUTPUT_DIR / 'pass2_raw_results.json'
    with open(raw_output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Raw results saved: {raw_output}")
    
    # Build final index
    build_final_index(results, approved)


def build_final_index(results: list, approved: list):
    """Build final index and generate LaTeX."""
    
    # Get chapter labels from main.tex
    project_root = Path(__file__).parent.parent
    chapter_labels = {}
    
    main_tex = project_root / 'main.tex'
    if main_tex.exists():
        with open(main_tex, 'r') as f:
            content = f.read()
        pattern = r'\\chapterwithsummaryfromfile\[([^\]]+)\]\{([^}]+)\}'
        for match in re.finditer(pattern, content):
            label = match.group(1)
            chapter_dir = match.group(2)
            for r in results:
                if r['chapter_dir'] == chapter_dir:
                    chapter_labels[r['chapter_num']] = label
                    break
    
    # Build index structure: subject -> subtopic -> [chapter_nums]
    index = {}
    
    for result in results:
        chapter_num = result['chapter_num']
        for entry in result.get('entries', []):
            subject = entry.get('subject', '').strip()
            subtopic = entry.get('subtopic')
            
            if not subject:
                continue
            
            # Normalize subject (find matching approved subject)
            subject_lower = subject.lower()
            matched_subject = None
            for a in approved:
                if a['subject'].lower() == subject_lower:
                    matched_subject = a['subject']
                    break
            
            if not matched_subject:
                # Try partial match
                for a in approved:
                    if subject_lower in a['subject'].lower() or a['subject'].lower() in subject_lower:
                        matched_subject = a['subject']
                        break
            
            if not matched_subject:
                # Subject not in approved list - SKIP IT
                continue
            
            if matched_subject not in index:
                index[matched_subject] = {}
            
            subtopic_key = subtopic.lower().strip() if subtopic else None
            
            if subtopic_key not in index[matched_subject]:
                index[matched_subject][subtopic_key] = []
            
            if chapter_num not in index[matched_subject][subtopic_key]:
                index[matched_subject][subtopic_key].append(chapter_num)
    
    # Post-process: Split combined subtopics like "dark matter and dark energy"
    # But keep some legitimate combined terms
    keep_combined = [
        'fields and forces',
        'formalism & notation',
        'error and bias',
    ]
    
    for subject in list(index.keys()):
        subtopics = index[subject]
        new_subtopics = {}
        for subtopic_key, chapters in list(subtopics.items()):
            # Check if should keep combined
            if subtopic_key and subtopic_key.lower() in [k.lower() for k in keep_combined]:
                # Keep as-is
                if subtopic_key not in new_subtopics:
                    new_subtopics[subtopic_key] = []
                for ch in chapters:
                    if ch not in new_subtopics[subtopic_key]:
                        new_subtopics[subtopic_key].append(ch)
            elif subtopic_key and ' and ' in subtopic_key:
                # Split "X and Y" into separate entries
                parts = [p.strip() for p in subtopic_key.split(' and ')]
                for part in parts:
                    if part not in new_subtopics:
                        new_subtopics[part] = []
                    for ch in chapters:
                        if ch not in new_subtopics[part]:
                            new_subtopics[part].append(ch)
                # Remove the combined entry
                del subtopics[subtopic_key]
            else:
                # Keep as-is
                if subtopic_key not in new_subtopics:
                    new_subtopics[subtopic_key] = []
                for ch in chapters:
                    if ch not in new_subtopics[subtopic_key]:
                        new_subtopics[subtopic_key].append(ch)
        
        # Merge new subtopics back
        for k, v in new_subtopics.items():
            if k not in subtopics:
                subtopics[k] = v
            else:
                for ch in v:
                    if ch not in subtopics[k]:
                        subtopics[k].append(ch)
    
    # Save final index
    final_output = OUTPUT_DIR / 'final_index.json'
    with open(final_output, 'w') as f:
        # Convert for JSON serialization
        serializable = {k: {str(sk): v for sk, v in sub.items()} for k, sub in index.items()}
        json.dump(serializable, f, indent=2, sort_keys=True)
    print(f"✅ Final index saved: {final_output}")
    
    # Generate LaTeX
    generate_latex(index, chapter_labels)


def generate_latex(index: dict, chapter_labels: dict):
    """Generate LaTeX subject_index_new.tex."""
    
    lines = [
        "% Subject Index - Beyond Popular Science",
        f"% Auto-generated by extract_subjects.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "% Two-pass extraction using Gemini 3 Pro Preview",
        "",
        "\\chapter*{Subject Index}",
        "\\markboth{SUBJECT INDEX}{SUBJECT INDEX}",
        "\\addcontentsline{toc}{chapter}{Subject Index}",
        "",
        "\\begin{multicols}{2}",
        "\\small",
        "\\setlength{\\parskip}{0.3em}",
        ""
    ]
    
    sorted_subjects = sorted(index.keys(), key=lambda x: x.lower())
    current_letter = None
    
    for subject in sorted_subjects:
        first_letter = subject[0].upper() if subject else '?'
        
        if first_letter != current_letter:
            if current_letter is not None:
                lines.append("")
            current_letter = first_letter
            lines.append(f"\\noindent\\textbf{{{first_letter}}}\\\\[0.3em]")
        
        subtopics = index[subject]
        
        # Get all chapters for this subject
        all_chapters = set()
        for chapters in subtopics.values():
            all_chapters.update(chapters)
        
        # Non-null subtopics
        named_subtopics = {k: v for k, v in subtopics.items() if k is not None}
        
        # Escape ampersand for LaTeX
        subject_escaped = subject.replace('&', '\\&')
        
        # Clean professional format: Bold subject, indented subtopics
        # But merge subtopics if they all point to the same pages
        if named_subtopics:
            # Group subtopics by their chapter sets
            chapter_to_subtopics = {}
            for subtopic, chapters in named_subtopics.items():
                key = tuple(sorted(chapters))
                if key not in chapter_to_subtopics:
                    chapter_to_subtopics[key] = []
                chapter_to_subtopics[key].append(subtopic)
            
            # If ALL subtopics share the exact same chapters, merge them inline
            if len(chapter_to_subtopics) == 1:
                key, subs = list(chapter_to_subtopics.items())[0]
                refs = []
                for ch in sorted(key):
                    if ch in chapter_labels:
                        refs.append(f"\\pageref{{{chapter_labels[ch]}}}")
                    else:
                        refs.append(str(ch))
                # Merge subtopics with commas in parentheses
                merged_subs = ', '.join(sorted(subs))
                lines.append(f"\\textbf{{{subject_escaped}}} ({merged_subs}), {', '.join(refs)}\\\\")
            else:
                # Different chapters for different subtopics - show hierarchy
                lines.append(f"\\textbf{{{subject_escaped}}}\\\\")
                
                for subtopic in sorted(named_subtopics.keys()):
                    chapters = named_subtopics[subtopic]
                    refs = []
                    for ch in sorted(chapters):
                        if ch in chapter_labels:
                            refs.append(f"\\pageref{{{chapter_labels[ch]}}}")
                        else:
                            refs.append(str(ch))
                    lines.append(f"\\hspace*{{1.5em}}{subtopic}, {', '.join(refs)}\\\\")
        else:
            # No subtopics - bold subject with page refs
            refs = []
            for ch in sorted(all_chapters):
                if ch in chapter_labels:
                    refs.append(f"\\pageref{{{chapter_labels[ch]}}}")
                else:
                    refs.append(str(ch))
            lines.append(f"\\textbf{{{subject_escaped}}}, {', '.join(refs)}\\\\")
    
    lines.extend([
        "",
        "\\end{multicols}",
        ""
    ])
    
    latex_output = OUTPUT_DIR / 'subject_index_new.tex'
    with open(latex_output, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ LaTeX index saved: {latex_output}")
    print(f"\n📊 Final Summary:")
    print(f"   Total subjects: {len(index)}")
    print(f"   Copy to replace subject_index.tex when ready")


# ============================================================================
# Main
# ============================================================================

def regenerate_latex():
    """Regenerate LaTeX from existing pass2 results."""
    print("Regenerating LaTeX from existing pass2 results...")
    
    # Load pass2 results
    pass2_file = OUTPUT_DIR / 'pass2_raw_results.json'
    if not pass2_file.exists():
        print(f"❌ ERROR: {pass2_file} not found! Run pass2 first.")
        sys.exit(1)
    
    with open(pass2_file) as f:
        results = json.load(f)
    
    # Load approved subjects
    candidates_file = OUTPUT_DIR / 'candidates.json'
    with open(candidates_file) as f:
        candidates = json.load(f)
    approved = [c for c in candidates if c.get('include', True)]
    
    build_final_index(results, approved)
    print("✅ Done!")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python extract_subjects.py pass1      # Extract candidates")
        print("  python extract_subjects.py pass2      # Classify with approved list")
        print("  python extract_subjects.py regenerate # Regenerate LaTeX from pass2 results")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == 'pass1':
        asyncio.run(run_pass1())
    elif command == 'pass2':
        asyncio.run(run_pass2())
    elif command == 'regenerate':
        regenerate_latex()
    else:
        print(f"Unknown command: {command}")
        print("Use 'pass1', 'pass2', or 'regenerate'")
        sys.exit(1)


if __name__ == "__main__":
    main()
