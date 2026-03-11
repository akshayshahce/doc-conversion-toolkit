from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException, UploadFile, status

ALLOWED_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif", "svg"}
ALLOWED_PDF_EXTS = {"pdf"}


def extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def ensure_allowed(file: UploadFile, allowed: set[str], kind: str) -> None:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unnamed {kind} file")
    ext = extension(file.filename)
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {kind} format '{ext}'. Allowed: {sorted(allowed)}",
        )


def parse_ranges(value: str, max_page: int) -> list[int]:
    pages: set[int] = set()
    for token in [part.strip() for part in value.split(",") if part.strip()]:
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            pages.add(int(token))

    out = sorted([p for p in pages if 1 <= p <= max_page])
    if not out:
        raise ValueError("No valid pages in requested range")
    return out


def zip_paths(paths: list[Path], target_zip: Path) -> Path:
    with ZipFile(target_zip, "w", compression=ZIP_DEFLATED) as zf:
        for p in paths:
            zf.write(p, arcname=p.name)
    return target_zip
