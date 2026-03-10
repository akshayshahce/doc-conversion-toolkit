import os
import io
import shutil
import subprocess
from tempfile import NamedTemporaryFile

import pikepdf
import fitz  # PyMuPDF

JPEGTRAN = shutil.which("jpegtran")

def bytes_mb(b): return round(b / (1024*1024), 2)

def optimize_jpeg_lossless(jpeg_bytes: bytes) -> bytes:
    """
    Losslessly optimize a JPEG using jpegtran.
    Returns original bytes if jpegtran is unavailable or fails.
    """
    if not JPEGTRAN:
        return jpeg_bytes
    with NamedTemporaryFile(suffix=".jpg", delete=False) as inp:
        inp.write(jpeg_bytes)
        inp.flush()
        inp_path = inp.name
    with NamedTemporaryFile(suffix=".jpg", delete=False) as outp:
        out_path = outp.name
    try:
        # -copy none: strip EXIF/ICC/XMP (no visual change), remove bloat
        # -optimize: better Huffman tables
        # -progressive: lossless transcode to progressive (smaller, same pixels)
        subprocess.run(
            [JPEGTRAN, "-copy", "none", "-optimize", "-progressive",
             "-outfile", out_path, inp_path],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        with open(out_path, "rb") as f:
            out_bytes = f.read()
        return out_bytes if len(out_bytes) <= len(jpeg_bytes) else jpeg_bytes
    except subprocess.CalledProcessError:
        return jpeg_bytes
    finally:
        try:
            os.remove(inp_path)
        except Exception:
            pass
        try:
            os.remove(out_path)
        except Exception:
            pass

def lossless_clean_pymupdf(input_pdf: str, output_pdf: str, strip_metadata: bool = True):
    doc = fitz.open(input_pdf)
    if strip_metadata:
        try:
            doc.set_metadata({})
        except Exception:
            pass
    doc.save(
        output_pdf,
        garbage=4,
        deflate=True,
        clean=True,
        incremental=False
    )
    doc.close()

def optimize_pdf_losslessly(input_pdf: str, output_pdf: str):
    before = os.path.getsize(input_pdf)

    # Pass 1: Losslessly optimize JPEG streams in-place using pikepdf
    with pikepdf.open(input_pdf, allow_overwriting_input=True) as pdf:
        num_replaced = 0
        for page in pdf.pages:
            # Iterate page resources for XObject images
            resources = page.get("/Resources", pikepdf.Dictionary())
            xobjs = resources.get("/XObject", pikepdf.Dictionary())
            for name, xobj in list(xobjs.items()):
                try:
                    # Only process image XObjects
                    if "/Subtype" in xobj and xobj["/Subtype"] == "/Image":
                        filters = xobj.get("/Filter", None)
                        # Normalize filters to a list for consistent checks
                        if isinstance(filters, pikepdf.Name):
                            filters = [filters]
                        # Only DCTDecode (JPEG) can be optimized via jpegtran
                        if filters and pikepdf.Name("/DCTDecode") in filters:
                            raw = bytes(xobj.stream_buffer)
                            opt = optimize_jpeg_lossless(raw)
                            if opt != raw:
                                xobj.stream = io.BytesIO(opt)
                                num_replaced += 1
                except Exception:
                    # Skip any problematic image
                    continue

        # Strip document-level metadata too (no visual impact)
        try:
            pdf.docinfo.clear()
        except Exception:
            pass

        pdf.save(output_pdf, linearize=False, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)

    # Pass 2: final structural clean/deflate with PyMuPDF (also lossless)
    tmp = output_pdf + ".tmp.pdf"
    os.replace(output_pdf, tmp)
    lossless_clean_pymupdf(tmp, output_pdf, strip_metadata=True)
    try:
        os.remove(tmp)
    except Exception:
        pass

    after = os.path.getsize(output_pdf)
    print(f"Input : {input_pdf}  ({bytes_mb(before)} MB)")
    print(f"Output: {output_pdf} ({bytes_mb(after)} MB)")
    print(f"Saved : {bytes_mb(max(0, before-after))} MB "
          f"({round(100*max(0, before-after)/before, 2) if before else 0}%)")

if __name__ == "__main__":
    # Change names if needed
    optimize_pdf_losslessly("merge.pdf", "merge_lossless_optimized.pdf")