import os
import re
from PyPDF2 import PdfMerger

def numeric_sort_key(filename):
    """
    Extracts a number from filename for natural sorting.
    Example: 'page_10.pdf' -> 10
    """
    match = re.search(r'(\d+)(?=\.pdf$)', filename)
    return int(match.group(1)) if match else float('inf')

def merge_pdfs(input_folder="pdf", output_pdf="merged_final.pdf"):
    """
    Merge all PDF files from a specific folder (default: 'pdf/')
    into one combined PDF in numeric order.
    """
    if not os.path.exists(input_folder):
        print(f"❌ Folder '{input_folder}' not found.")
        return

    # Collect all PDFs
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"❌ No PDF files found in '{input_folder}' folder.")
        return

    # Sort numerically then alphabetically
    pdf_files.sort(key=lambda x: (numeric_sort_key(x), x.lower()))

    merger = PdfMerger()

    print(f"Merging {len(pdf_files)} PDFs from '{input_folder}' in order:")
    for filename in pdf_files:
        filepath = os.path.join(input_folder, filename)
        print(f"  ➜ {filename}")
        merger.append(filepath)

    # Write final merged file
    merger.write(output_pdf)
    merger.close()

    print(f"\n✅ Successfully merged into '{output_pdf}'")

if __name__ == "__main__":
    merge_pdfs(input_folder="pdf", output_pdf="merged_final.pdf")