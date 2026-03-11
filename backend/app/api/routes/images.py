from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.app.schemas.images import ImageCompressionMode, ImageToPdfOptions
from backend.app.services.image_service import (
    compress_image_bytes,
    convert_image_bytes,
    image_media_type,
    images_to_pdf,
    resize_image_bytes,
)
from backend.app.utils.files import ALLOWED_IMAGE_EXTS, ensure_allowed
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


@router.post("/convert")
async def convert_images(
    files: list[UploadFile] = File(...),
    output_format: str = Form(...),
    background_color: str = Form("#FFFFFF"),
):
    if output_format.lower() not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported output format")

    with workspace() as work:
        output_dir = work / "converted"
        output_dir.mkdir(parents=True, exist_ok=True)

        out_files: list[Path] = []
        for file in files:
            ensure_allowed(file, ALLOWED_IMAGE_EXTS, "image")
            data = await file.read()
            converted = convert_image_bytes(data, output_format, background_color)
            target = output_dir / f"{Path(file.filename).stem}.{output_format.lower()}"
            target.write_bytes(converted)
            out_files.append(target)

        if len(out_files) == 1:
            only = out_files[0]
            return file_bytes_response(path=only, media_type="application/octet-stream", filename=only.name)

        from backend.app.utils.files import zip_paths

        archive = zip_paths(out_files, work / "converted_images.zip")
        return file_bytes_response(path=archive, media_type="application/zip", filename=archive.name)


@router.post("/resize")
async def resize_images(
    files: list[UploadFile] = File(...),
    width: int = Form(...),
    height: int = Form(...),
    keep_aspect_ratio: bool = Form(True),
):
    if width < 1 or height < 1 or width > 10000 or height > 10000:
        raise HTTPException(status_code=400, detail="Width and height must be between 1 and 10000")

    with workspace() as work:
        output_dir = work / "resized"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_files: list[Path] = []

        for file in files:
            ensure_allowed(file, ALLOWED_IMAGE_EXTS, "image")
            data = await file.read()
            resized = resize_image_bytes(data, width, height, keep_aspect_ratio)
            target = output_dir / file.filename
            target.write_bytes(resized)
            out_files.append(target)

        if len(out_files) == 1:
            only = out_files[0]
            return file_bytes_response(path=only, media_type="application/octet-stream", filename=only.name)

        from backend.app.utils.files import zip_paths

        archive = zip_paths(out_files, work / "resized_images.zip")
        return file_bytes_response(path=archive, media_type="application/zip", filename=archive.name)


@router.post("/compress")
async def compress_images(
    files: list[UploadFile] = File(...),
    mode: ImageCompressionMode = Form(ImageCompressionMode.high_quality),
    strip_metadata: bool = Form(False),
    target_reduction_percent: int | None = Form(default=None),
    force_reduce_size: bool = Form(False),
    compression_level: int | None = Form(default=None),
    quality: int | None = Form(default=None),
    colors: int | None = Form(default=None),
    precision: int | None = Form(default=None),
):
    if target_reduction_percent is not None and not 0 <= target_reduction_percent <= 99:
        raise HTTPException(status_code=400, detail="target_reduction_percent must be between 0 and 99")
    if compression_level is not None and not 0 <= compression_level <= 99:
        raise HTTPException(status_code=400, detail="compression_level must be between 0 and 99")
    if quality is not None and not 0 <= quality <= 100:
        raise HTTPException(status_code=400, detail="quality must be between 0 and 100")
    if colors is not None and not 2 <= colors <= 256:
        raise HTTPException(status_code=400, detail="colors must be between 2 and 256")
    if precision is not None and not 0 <= precision <= 3:
        raise HTTPException(status_code=400, detail="precision must be between 0 and 3")
    with workspace() as work:
        output_dir = work / "compressed"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_files: list[Path] = []

        for file in files:
            ensure_allowed(file, ALLOWED_IMAGE_EXTS, "image")
            ext = Path(file.filename).suffix.lower().lstrip(".")
            data = await file.read()
            compressed = compress_image_bytes(
                data,
                ext,
                mode,
                strip_metadata,
                target_reduction_percent,
                force_reduce_size,
                compression_level,
                quality,
                colors,
                precision,
            )
            target = output_dir / file.filename
            target.write_bytes(compressed)
            out_files.append(target)

        if len(out_files) == 1:
            only = out_files[0]
            headers = _compression_headers(len(data), len(compressed), target_reduction_percent, force_reduce_size)
            return file_bytes_response(path=only, media_type=image_media_type(ext), filename=only.name, extra_headers=headers)

        from backend.app.utils.files import zip_paths

        archive = zip_paths(out_files, work / "compressed_images.zip")
        return file_bytes_response(path=archive, media_type="application/zip", filename=archive.name)


@router.post("/compress-preview")
async def compress_image_preview(
    file: UploadFile = File(...),
    mode: ImageCompressionMode = Form(ImageCompressionMode.high_quality),
    strip_metadata: bool = Form(False),
    target_reduction_percent: int | None = Form(default=None),
    force_reduce_size: bool = Form(False),
    compression_level: int | None = Form(default=None),
    quality: int | None = Form(default=None),
    colors: int | None = Form(default=None),
    precision: int | None = Form(default=None),
):
    if target_reduction_percent is not None and not 0 <= target_reduction_percent <= 99:
        raise HTTPException(status_code=400, detail="target_reduction_percent must be between 0 and 99")
    if compression_level is not None and not 0 <= compression_level <= 99:
        raise HTTPException(status_code=400, detail="compression_level must be between 0 and 99")
    if quality is not None and not 0 <= quality <= 100:
        raise HTTPException(status_code=400, detail="quality must be between 0 and 100")
    if colors is not None and not 2 <= colors <= 256:
        raise HTTPException(status_code=400, detail="colors must be between 2 and 256")
    if precision is not None and not 0 <= precision <= 3:
        raise HTTPException(status_code=400, detail="precision must be between 0 and 3")

    ensure_allowed(file, ALLOWED_IMAGE_EXTS, "image")
    ext = Path(file.filename).suffix.lower().lstrip(".")
    data = await file.read()
    compressed = compress_image_bytes(
        data,
        ext,
        mode,
        strip_metadata,
        target_reduction_percent,
        force_reduce_size,
        compression_level,
        quality,
        colors,
        precision,
    )
    headers = _compression_headers(len(data), len(compressed), target_reduction_percent, force_reduce_size)
    return Response(content=compressed, media_type=image_media_type(ext), headers=headers)


@router.post("/to-pdf")
async def convert_images_to_pdf(
    files: list[UploadFile] = File(...),
    page_size: str = Form("original"),
    fit_to_page: bool = Form(True),
    filename: str = Form("images.pdf"),
):
    with workspace() as work:
        input_dir = work / "images"
        input_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []

        for idx, file in enumerate(files, start=1):
            ensure_allowed(file, ALLOWED_IMAGE_EXTS, "image")
            target = input_dir / f"{idx:03d}_{file.filename}"
            target.write_bytes(await file.read())
            paths.append(target)

        options = ImageToPdfOptions(page_size=page_size, fit_to_page=fit_to_page, filename=filename)
        output_pdf = images_to_pdf(paths, work / filename, options)
        return file_bytes_response(path=output_pdf, media_type="application/pdf", filename=filename)
