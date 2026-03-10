from PIL import Image
import os
import re

def images_to_pdf(input_folder="output_images", output_pdf="merged.pdf"):
    """
    Combine images from a folder into a single PDF in numeric order:
    page_1.png, page_2.png, ..., page_10.png, etc.
    """

    def page_index(filename: str) -> int:
        # Try to extract the last number before the file extension; fallback to any number in name
        m = re.search(r'(\d+)(?=\.[^.]+$)', filename) or re.search(r'(\d+)', filename)
        return int(m.group(1)) if m else float('inf')

    # Collect images (case-insensitive extensions)
    image_files = [f for f in os.listdir(input_folder)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'))]

    if not image_files:
        print("❌ No images found.")
        return

    # Sort by numeric page index, then by name to stabilize ties
    image_files.sort(key=lambda f: (page_index(f), f.lower()))

    # Open images and convert to RGB for PDF
    images = []
    for name in image_files:
        path = os.path.join(input_folder, name)
        img = Image.open(path)
        if img.mode in ("RGBA", "P"):  # PDF pages don't support alpha
            img = img.convert("RGB")
        else:
            img = img.copy()  # detach from file handle
        images.append(img)

    # Save: first image + append the rest
    first, rest = images[0], images[1:]
    first.save(output_pdf, save_all=True, append_images=rest)

    # Cleanup
    for im in images:
        im.close()

    print(f"✅ PDF created in sequence: {output_pdf}")

if __name__ == "__main__":
    images_to_pdf(input_folder="output_images", output_pdf="merged.pdf")