from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.schemas.pdf import PdfCompressionMode, PdfToImageOptions
from backend.app.services.pdf_service import (
    compress_pdf,
    delete_pages,
    extract_pages,
    merge_pdfs,
    pdf_to_images,
    reorder_pages,
    rotate_pages,
    split_pdf_by_ranges,
)
from backend.app.utils.files import ALLOWED_PDF_EXTS, ensure_allowed, parse_ranges, zip_paths
from backend.app.utils.http_response import file_bytes_response
from backend.app.utils.temp_workspace import workspace

router = APIRouter()


def _compression_headers(
    original_size: int,
    output_size: int,
    target_reduction_percent: int | None,
    force_reduce_size: bool,
) -> dict[str, str]:
    reduction_percent = 0.0
    if original_size > 0:
        reduction_percent = max(0.0, (original_size - output_size) * 100.0 / original_size)
    target_achieved = False
    if target_reduction_percent is not None:
        target_achieved = reduction_percent >= float(target_reduction_percent)
    return {
        "X-Original-Size": str(original_size),
        "X-Output-Size": str(output_size),
        "X-Reduction-Percent": f"{reduction_percent:.2f}",
        "X-Target-Reduction-Percent": str(target_reduction_percent or ""),
        "X-Target-Achieved": "true" if target_achieved else "false",
        "X-Force-Reduce-Size": "true" if force_reduce_size else "false",
    }


@router.post("/to-images")
async def convert_pdf_to_images(
    file: UploadFile = File(...),
    format: str = Form("png"),
    dpi: int = Form(300),
    page_range: str | None = Form(None),
):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    with workspace() as work:
        source = work / file.filename
        source.write_bytes(await file.read())

        options = PdfToImageOptions(format=format, dpi=dpi, page_range=page_range)
        out_dir = work / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_paths = pdf_to_images(source, out_dir, options)

        if len(output_paths) == 1:
            only = output_paths[0]
            return file_bytes_response(path=only, media_type="application/octet-stream", filename=only.name)

        archive = zip_paths(output_paths, work / "pdf_images.zip")
        return file_bytes_response(path=archive, media_type="application/zip", filename=archive.name)


@router.post("/compress")
async def compress_pdf_route(
    file: UploadFile = File(...),
    mode: PdfCompressionMode = Form(PdfCompressionMode.quality_first),
    target_reduction_percent: int | None = Form(default=None),
    force_reduce_size: bool = Form(False),
):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    if target_reduction_percent is not None and not 1 <= target_reduction_percent <= 90:
        raise HTTPException(status_code=400, detail="target_reduction_percent must be between 1 and 90")
    with workspace() as work:
        source = work / file.filename
        source_bytes = await file.read()
        source.write_bytes(source_bytes)
        target = work / f"compressed_{file.filename}"
        compress_pdf(source, target, mode, target_reduction_percent, force_reduce_size)
        headers = _compression_headers(len(source_bytes), target.stat().st_size, target_reduction_percent, force_reduce_size)
        return file_bytes_response(path=target, media_type="application/pdf", filename=target.name, extra_headers=headers)


@router.post("/merge")
async def merge_pdf_route(files: list[UploadFile] = File(...)):
    with workspace() as work:
        pdfs: list[Path] = []
        for idx, file in enumerate(files, start=1):
            ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
            p = work / f"{idx:03d}_{file.filename}"
            p.write_bytes(await file.read())
            pdfs.append(p)
        output = work / "merged.pdf"
        merge_pdfs(pdfs, output)
        return file_bytes_response(path=output, media_type="application/pdf", filename=output.name)


@router.post("/split")
async def split_pdf_route(file: UploadFile = File(...), ranges: str = Form(...)):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    with workspace() as work:
        src = work / file.filename
        src.write_bytes(await file.read())
        parsed_ranges: list[tuple[int, int]] = []
        for token in [x.strip() for x in ranges.split(",") if x.strip()]:
            if "-" not in token:
                raise HTTPException(status_code=400, detail="Ranges must be like 1-3,5-8")
            s, e = token.split("-", 1)
            parsed_ranges.append((int(s), int(e)))

        out_dir = work / "split"
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs = split_pdf_by_ranges(src, parsed_ranges, out_dir)
        archive = zip_paths(outputs, work / "split_pdf.zip")
        return file_bytes_response(path=archive, media_type="application/zip", filename=archive.name)


@router.post("/extract")
async def extract_pages_route(file: UploadFile = File(...), pages: str = Form(...)):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    with workspace() as work:
        src = work / file.filename
        src.write_bytes(await file.read())
        import pypdf

        total = len(pypdf.PdfReader(str(src)).pages)
        parsed = parse_ranges(pages, total)
        output = work / "extracted_pages.pdf"
        extract_pages(src, parsed, output)
        return file_bytes_response(path=output, media_type="application/pdf", filename=output.name)


@router.post("/rotate")
async def rotate_pages_route(
    file: UploadFile = File(...),
    pages: str = Form(...),
    degrees: int = Form(90),
):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    if degrees not in {90, 180, 270}:
        raise HTTPException(status_code=400, detail="Degrees must be one of: 90, 180, 270")

    with workspace() as work:
        src = work / file.filename
        src.write_bytes(await file.read())
        import pypdf

        total = len(pypdf.PdfReader(str(src)).pages)
        parsed = parse_ranges(pages, total)
        output = work / "rotated.pdf"
        rotate_pages(src, parsed, degrees, output)
        return file_bytes_response(path=output, media_type="application/pdf", filename=output.name)


@router.post("/delete")
async def delete_pages_route(file: UploadFile = File(...), pages: str = Form(...)):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    with workspace() as work:
        src = work / file.filename
        src.write_bytes(await file.read())
        import pypdf

        total = len(pypdf.PdfReader(str(src)).pages)
        parsed = parse_ranges(pages, total)
        output = work / "pages_deleted.pdf"
        delete_pages(src, parsed, output)
        return file_bytes_response(path=output, media_type="application/pdf", filename=output.name)


@router.post("/reorder")
async def reorder_pages_route(file: UploadFile = File(...), order: str = Form(...)):
    ensure_allowed(file, ALLOWED_PDF_EXTS, "pdf")
    with workspace() as work:
        src = work / file.filename
        src.write_bytes(await file.read())
        import pypdf

        total = len(pypdf.PdfReader(str(src)).pages)
        parsed = [int(x.strip()) for x in order.split(",") if x.strip()]
        if sorted(parsed) != list(range(1, total + 1)):
            raise HTTPException(status_code=400, detail="Order must include each page exactly once")
        output = work / "reordered.pdf"
        reorder_pages(src, parsed, output)
        return file_bytes_response(path=output, media_type="application/pdf", filename=output.name)
