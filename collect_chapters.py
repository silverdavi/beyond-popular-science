import os
import glob

def get_chapter_content():
    chapters = sorted(glob.glob("[0-9][0-9]_*"))
    output_file = "temp_chapters_content.txt"
    
    with open(output_file, "w", encoding="utf-8") as outfile:
        for chapter_dir in chapters:
            chapter_num = chapter_dir.split("_")[0]
            subject = "_".join(chapter_dir.split("_")[1:])
            
            outfile.write(f"=== CHAPTER_START: {chapter_num} | {subject} ===\n")
            
            tex_files = glob.glob(os.path.join(chapter_dir, "*.tex"))
            for tex_file in tex_files:
                try:
                    with open(tex_file, "r", encoding="utf-8") as infile:
                        outfile.write(f"--- FILE: {os.path.basename(tex_file)} ---\n")
                        outfile.write(infile.read())
                        outfile.write("\n")
                except Exception as e:
                    outfile.write(f"Error reading {tex_file}: {e}\n")
            
            outfile.write(f"=== CHAPTER_END ===\n\n")
            
    print(f"Written content to {output_file}")

if __name__ == "__main__":
    get_chapter_content()

