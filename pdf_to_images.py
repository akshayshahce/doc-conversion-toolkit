import fitz  # PyMuPDF
import os
from math import ceil

def pdf_to_images(
    pdf_path: str,
    output_folder: str = "output_images",
    dpi: int = 400,                 # 300–600 is typical for sharp text
    image_format: str = "png",      # "png" (lossless) or "jpg"
    jpeg_quality: int = 95,         # if image_format="jpg"
    flatten_transparency: bool = True,  # replace alpha with white bg
):
    """
    Render each PDF page to an image at the requested DPI.

    Args:
        pdf_path: input PDF file
        output_folder: destination folder
        dpi: render resolution (pixels per inch). 72 is 1x; 300–600 recommended.
        image_format: "png" (lossless) or "jpg"
        jpeg_quality: JPEG quality (1–100) if using JPG
        flatten_transparency: if True, removes alpha (white background)
    """
    os.makedirs(output_folder, exist_ok=True)

    doc = fitz.open(pdf_path)
    print(f"Converting '{pdf_path}' ({doc.page_count} pages) at {dpi} DPI → {image_format.upper()}")

    # scale factor relative to 72 dpi
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)

    for i in range(doc.page_count):
        page = doc.load_page(i)

        # Render to pixmap at the target DPI
        pix = page.get_pixmap(matrix=mat, alpha=not flatten_transparency)

        # If we want to ensure no alpha (some viewers dislike it), convert to RGB
        if flatten_transparency and pix.alpha:
            pix = fitz.Pixmap(fitz.csRGB, pix)  # drops alpha on white

        # Build output path
        idx = i + 1
        ext = image_format.lower()
        out_path = os.path.join(output_folder, f"page_{idx}.{ext}")

        if ext in ("jpg", "jpeg"):
            # Save as high quality JPEG
            pix.save(out_path, output="jpg", jpg_quality=jpeg_quality, jpg_progressive=False, jpg_optimize=True)
        else:
            # Lossless PNG
            pix.save(out_path)

        print(f"Saved: {out_path}  ({pix.width}x{pix.height}px)")

    doc.close()
    print(f"\n✅ Done! Images are in '{output_folder}'")

if __name__ == "__main__":
    pdf_file = "PassportAllPages.pdf"  # your file
    # Try 400–600 DPI for tiny details like stamps or fine text
    pdf_to_images(pdf_file, output_folder="output_images", dpi=400, image_format="png")