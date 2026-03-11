from __future__ import annotations

from pathlib import Path

import fitz
from pypdf import PdfReader, PdfWriter

from backend.app.schemas.pdf import PdfCompressionMode, PdfToImageOptions


def pdf_to_images(pdf_path: Path, out_dir: Path, options: PdfToImageOptions) -> list[Path]:
    doc = fitz.open(pdf_path)
    try:
        pages = list(range(1, doc.page_count + 1))
        if options.page_range:
            from backend.app.utils.files import parse_ranges

            pages = parse_ranges(options.page_range, doc.page_count)

        out_paths: list[Path] = []
        scale = options.dpi / 72.0
        mat = fitz.Matrix(scale, scale)

        for p in pages:
            pix = doc.load_page(p - 1).get_pixmap(matrix=mat, alpha=False)
            out_path = out_dir / f"page_{p:03d}.{options.format.value}"
            if options.format.value == "png":
                pix.save(str(out_path))
            elif options.format.value == "jpeg":
                pix.save(str(out_path), output="jpg", jpg_quality=94)
            else:
                pix.save(str(out_path), output="webp")
            out_paths.append(out_path)

        return out_paths
    finally:
        doc.close()


def _reencode_embedded_images(doc: fitz.Document, quality: int) -> None:
    for xref in range(1, doc.xref_length()):
        if doc.xref_get_key(xref, "Subtype")[1] != "/Image":
            continue
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            encoded = pix.tobytes("jpeg", jpg_quality=quality)
            doc.update_stream(xref, encoded)
        except Exception:
            continue


def compress_pdf(
    input_pdf: Path,
    output_pdf: Path,
    mode: PdfCompressionMode,
    target_reduction_percent: int | None = None,
    force_reduce_size: bool = False,
) -> Path:
    original_bytes = input_pdf.read_bytes()
    original_size = len(original_bytes)
    target_size = None
    if target_reduction_percent:
        target_size = int(original_size * (1 - target_reduction_percent / 100.0))

    candidates: list[tuple[bool, int | None, dict[str, int | bool]]] = []
    if mode == PdfCompressionMode.quality_first:
        candidates = [(False, None, {"garbage": 3, "deflate": True, "clean": True, "incremental": False})]
    elif mode == PdfCompressionMode.light:
        candidates = [(False, None, {"garbage": 4, "deflate": True, "clean": True, "incremental": False})]
    elif mode == PdfCompressionMode.balanced:
        candidates = [(False, None, {"garbage": 4, "deflate": True, "clean": True, "incremental": False, "use_objstms": 1})]
    else:
        candidates = [(True, 82, {"garbage": 4, "deflate": True, "clean": True, "incremental": False, "use_objstms": 1})]

    if target_reduction_percent or force_reduce_size:
        candidates.extend(
            [
                (True, 82, {"garbage": 4, "deflate": True, "clean": True, "incremental": False, "use_objstms": 1}),
                (True, 76, {"garbage": 4, "deflate": True, "clean": True, "incremental": False, "use_objstms": 1}),
                (True, 70, {"garbage": 4, "deflate": True, "clean": True, "incremental": False, "use_objstms": 1}),
                (True, 64, {"garbage": 4, "deflate": True, "clean": True, "incremental": False, "use_objstms": 1}),
            ]
        )

    best_bytes = original_bytes
    for reencode, quality, save_kwargs in candidates:
        doc = fitz.open(input_pdf)
        try:
            if reencode and quality is not None:
                _reencode_embedded_images(doc, quality)
            doc.save(str(output_pdf), **save_kwargs)
        finally:
            doc.close()

        candidate = output_pdf.read_bytes()
        if len(candidate) < len(best_bytes):
            best_bytes = candidate

        if target_size and len(best_bytes) <= target_size:
            break
        if force_reduce_size and len(best_bytes) < original_size:
            break

    # Keep original if no reduction is possible.
    if len(best_bytes) >= original_size:
        output_pdf.write_bytes(original_bytes)
    else:
        output_pdf.write_bytes(best_bytes)
    return output_pdf


def merge_pdfs(pdf_paths: list[Path], output_pdf: Path) -> Path:
    writer = PdfWriter()
    for path in pdf_paths:
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    with output_pdf.open("wb") as f:
        writer.write(f)
    return output_pdf


def split_pdf_by_ranges(pdf_path: Path, ranges: list[tuple[int, int]], out_dir: Path) -> list[Path]:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    out_files: list[Path] = []

    for idx, (start, end) in enumerate(ranges, start=1):
        writer = PdfWriter()
        for p in range(max(1, start), min(total, end) + 1):
            writer.add_page(reader.pages[p - 1])
        out = out_dir / f"split_{idx}_{start}-{end}.pdf"
        with out.open("wb") as f:
            writer.write(f)
        out_files.append(out)

    return out_files


def extract_pages(pdf_path: Path, pages: list[int], output_pdf: Path) -> Path:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for p in pages:
        writer.add_page(reader.pages[p - 1])
    with output_pdf.open("wb") as f:
        writer.write(f)
    return output_pdf


def rotate_pages(pdf_path: Path, pages: list[int], degrees: int, output_pdf: Path) -> Path:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for idx, page in enumerate(reader.pages, start=1):
        if idx in pages:
            page.rotate(degrees)
        writer.add_page(page)
    with output_pdf.open("wb") as f:
        writer.write(f)
    return output_pdf


def delete_pages(pdf_path: Path, pages: list[int], output_pdf: Path) -> Path:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for idx, page in enumerate(reader.pages, start=1):
        if idx not in pages:
            writer.add_page(page)
    with output_pdf.open("wb") as f:
        writer.write(f)
    return output_pdf


def reorder_pages(pdf_path: Path, order: list[int], output_pdf: Path) -> Path:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for idx in order:
        writer.add_page(reader.pages[idx - 1])
    with output_pdf.open("wb") as f:
        writer.write(f)
    return output_pdf
