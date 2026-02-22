#!/usr/bin/env python3
"""
Consolidate and clean up the candidate subjects using Gemini.
Reduces ~1100 subjects to a cleaner, hierarchical structure.
"""

import os
import json
import asyncio
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
MODEL_NAME = "gemini-3-pro-preview"

def load_env():
    env_paths = [Path(__file__).parent.parent / '.env', Path.cwd() / '.env']
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        k, v = line.strip().split('=', 1)
                        os.environ[k] = v.strip().strip('"').strip("'")
            break

CONSOLIDATION_PROMPT = """You are creating a professional subject index for a science book.

I have {count} raw subject entries extracted from chapters. Many are:
- Duplicates with slightly different wording
- Too specific (should be subtopics under broader subjects)
- People names that should be grouped under "People" or kept as-is if famous
- Acronyms that should be expanded or grouped

Your task: Consolidate these into a CLEAN list of 200-300 well-organized subjects.

Rules:
1. KEEP famous names as their own subjects (Einstein, Newton, Feynman, etc.)
2. MERGE obscure names under their field or remove if not significant
3. MERGE overly specific topics under broader subjects
4. STANDARDIZE naming (e.g., "Quantum mechanics" not "QM" or "Quantum theory")
5. Each subject should have 2-8 subtopics maximum
6. Prefer established terminology

Here are the raw subjects (JSON array):
{subjects_json}

Return a JSON object:
{{
  "consolidated": [
    {{"subject": "Broad Subject", "subtopics": ["sub1", "sub2"], "merged_from": ["original1", "original2"]}},
    ...
  ],
  "removed": ["subject names that were too specific or duplicates and were absorbed elsewhere"]
}}

Return ONLY valid JSON.
"""


async def consolidate_batch(subjects_batch: list, model, batch_num: int) -> dict:
    """Consolidate a batch of subjects."""
    print(f"  Processing batch {batch_num} ({len(subjects_batch)} subjects)...")
    
    subjects_json = json.dumps([s['subject'] for s in subjects_batch], indent=1)
    
    prompt = CONSOLIDATION_PROMPT.format(
        count=len(subjects_batch),
        subjects_json=subjects_json
    )
    
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        
        if text.startswith('```'):
            import re
            text = re.sub(r'^```json?\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
        
        return json.loads(text)
    except Exception as e:
        print(f"    Error: {e}")
        return {"consolidated": [], "removed": []}


async def main():
    print("=" * 70)
    print("CONSOLIDATING SUBJECTS")
    print(f"Model: {MODEL_NAME}")
    print("=" * 70)
    
    load_env()
    
    import google.generativeai as genai
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Load candidates
    with open(OUTPUT_DIR / 'candidates.json') as f:
        candidates = json.load(f)
    
    print(f"\n📖 Original subjects: {len(candidates)}")
    
    # Split into batches for processing (Gemini context limits)
    batch_size = 150
    batches = [candidates[i:i+batch_size] for i in range(0, len(candidates), batch_size)]
    
    print(f"📦 Processing in {len(batches)} batches of ~{batch_size}...\n")
    
    # Process all batches in parallel
    tasks = [consolidate_batch(batch, model, i+1) for i, batch in enumerate(batches)]
    results = await asyncio.gather(*tasks)
    
    # Merge all consolidated results
    all_consolidated = []
    all_removed = []
    
    for result in results:
        all_consolidated.extend(result.get('consolidated', []))
        all_removed.extend(result.get('removed', []))
    
    print(f"\n📊 After batch consolidation: {len(all_consolidated)} subjects")
    
    # Second pass: Deduplicate across batches
    print("\n🔄 Deduplicating across batches...")
    
    seen = {}
    final_consolidated = []
    
    for item in all_consolidated:
        subj = item['subject'].lower().strip()
        if subj not in seen:
            seen[subj] = item
            final_consolidated.append(item)
        else:
            # Merge subtopics
            existing = seen[subj]
            existing_subtopics = set(existing.get('subtopics', []))
            new_subtopics = set(item.get('subtopics', []))
            existing['subtopics'] = list(existing_subtopics | new_subtopics)
    
    print(f"✅ Final subjects: {len(final_consolidated)}")
    
    # Save consolidated list
    consolidated_output = OUTPUT_DIR / 'candidates_consolidated.json'
    
    # Convert to the format expected by pass2
    final_for_pass2 = []
    for item in sorted(final_consolidated, key=lambda x: x['subject'].lower()):
        final_for_pass2.append({
            'subject': item['subject'],
            'subtopics': item.get('subtopics', [])[:8],  # Max 8 subtopics
            'include': True
        })
    
    with open(consolidated_output, 'w') as f:
        json.dump(final_for_pass2, f, indent=2)
    
    print(f"\n✅ Saved: {consolidated_output}")
    print(f"   Total subjects: {len(final_for_pass2)}")
    print(f"   Total subtopics: {sum(len(x['subtopics']) for x in final_for_pass2)}")
    
    # Also show what was removed
    removed_output = OUTPUT_DIR / 'subjects_removed.json'
    with open(removed_output, 'w') as f:
        json.dump(sorted(set(all_removed)), f, indent=2)
    
    print(f"   Removed subjects: {len(set(all_removed))} (see {removed_output})")
    
    print(f"\n📝 NEXT STEPS:")
    print(f"   1. Review: {consolidated_output}")
    print(f"   2. Copy to candidates.json: cp {consolidated_output} {OUTPUT_DIR}/candidates.json")
    print(f"   3. Run: python extract_subjects.py pass2")


if __name__ == "__main__":
    asyncio.run(main())
