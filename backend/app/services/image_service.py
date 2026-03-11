from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from backend.app.schemas.images import ImageCompressionMode, ImageToPdfOptions

PAGE_SIZES = {
    "a4": A4,
    "letter": LETTER,
}


def _flatten_if_needed(img: Image.Image, out_format: str, background_color: str) -> Image.Image:
    if out_format.lower() in {"jpg", "jpeg"} and img.mode in {"RGBA", "LA", "P"}:
        base = Image.new("RGB", img.size, background_color)
        alpha = img.convert("RGBA")
        base.paste(alpha, mask=alpha.split()[3])
        return base
    if img.mode in {"RGBA", "LA", "P"} and out_format.lower() not in {"png", "webp", "tiff"}:
        return img.convert("RGB")
    return img


def convert_image_bytes(data: bytes, out_format: str, background_color: str = "#FFFFFF") -> bytes:
    with Image.open(BytesIO(data)) as img:
        oriented = ImageOps.exif_transpose(img)
        prepared = _flatten_if_needed(oriented, out_format, background_color)
        if prepared.mode not in {"RGB", "L", "RGBA"}:
            prepared = prepared.convert("RGB")

        out = BytesIO()
        save_kwargs: dict[str, int | bool] = {}
        ext = out_format.lower()
        if ext in {"jpg", "jpeg"}:
            save_kwargs = {"quality": 95, "optimize": True, "progressive": True}
        elif ext == "webp":
            save_kwargs = {"quality": 95, "method": 6}
        elif ext in {"png", "tiff"}:
            save_kwargs = {"optimize": True}

        prepared.save(out, format="JPEG" if ext == "jpg" else ext.upper(), **save_kwargs)
        return out.getvalue()


def resize_image_bytes(
    data: bytes,
    width: int,
    height: int,
    keep_aspect_ratio: bool = True,
) -> bytes:
    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)
        original_format = (img.format or "PNG").upper()
        format_name = "JPEG" if original_format == "JPG" else original_format

        if keep_aspect_ratio:
            # Fit inside target bounds while preserving source aspect ratio.
            resized = ImageOps.contain(img, (width, height), Image.Resampling.LANCZOS)
        else:
            resized = img.resize((width, height), Image.Resampling.LANCZOS)

        out = BytesIO()
        kwargs: dict[str, int | bool] = {}

        if format_name == "JPEG":
            if resized.mode in {"RGBA", "LA", "P"}:
                resized = resized.convert("RGB")
            kwargs = {"quality": 95, "optimize": True, "progressive": True}
        elif format_name == "WEBP":
            kwargs = {"quality": 95, "method": 6}
        elif format_name == "PNG":
            kwargs = {"optimize": True}

        resized.save(out, format=format_name, **kwargs)
        return out.getvalue()


def compress_image_bytes(
    data: bytes,
    ext: str,
    mode: ImageCompressionMode,
    strip_metadata: bool,
    target_reduction_percent: int | None = None,
    force_reduce_size: bool = False,
    compression_level: int | None = None,
    quality_override: int | None = None,
    palette_colors: int | None = None,
    svg_precision: int | None = None,
) -> bytes:
    normalized_ext = ext.lower().lstrip(".")
    if normalized_ext == "svg":
        precision = 2 if svg_precision is None else max(0, min(3, svg_precision))

        def round_decimal(match: re.Match[str]) -> str:
            number = float(match.group(0))
            text = f"{number:.{precision}f}"
            return text.rstrip("0").rstrip(".") if "." in text else text

        return re.sub(r"-?\d+\.\d+", round_decimal, data.decode("utf-8")).encode("utf-8")

    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)
        out = BytesIO()
        fmt = "JPEG" if ext in {"jpg", "jpeg"} else ext.upper()
        exif = None if strip_metadata else img.info.get("exif")

        def jpeg_save(target: BytesIO, quality: int) -> None:
            kwargs: dict[str, int | bool | bytes] = {
                "format": fmt,
                "quality": quality,
                "optimize": True,
                "progressive": True,
            }
            if exif is not None:
                kwargs["exif"] = exif
            img.save(target, **kwargs)

        level = None if compression_level is None else max(0, min(99, compression_level))
        quality = None if quality_override is None else max(0, min(100, quality_override))
        colors = None if palette_colors is None else max(2, min(256, palette_colors))

        if quality is not None and fmt == "JPEG":
            jpeg_save(out, max(12, quality))
        elif quality is not None and fmt == "WEBP":
            img.save(out, format=fmt, quality=max(10, quality), method=6)
        elif colors is not None and fmt in {"PNG", "GIF"}:
            source_for_palette = img.convert("RGB")
            pal = source_for_palette.quantize(colors=colors)
            if fmt == "PNG":
                pal.save(out, format="PNG", optimize=True, compress_level=9)
            else:
                pal.save(out, format="GIF", optimize=True)
        elif level is not None:
            if fmt == "JPEG":
                jpeg_quality = max(12, 95 - int(level * 0.8))
                jpeg_save(out, jpeg_quality)
            elif fmt == "WEBP":
                webp_quality = max(10, 95 - int(level * 0.8))
                img.save(out, format=fmt, quality=webp_quality, method=6)
            elif fmt in {"PNG", "GIF", "BMP", "TIFF"}:
                # For palette-friendly formats, stronger compression reduces the palette progressively.
                source_for_palette = img.convert("RGB")
                colors = max(16, 256 - int(level * 2.2))
                pal = source_for_palette.quantize(colors=colors)
                if fmt == "PNG":
                    pal.save(out, format="PNG", optimize=True, compress_level=9)
                elif fmt == "GIF":
                    pal.save(out, format="GIF", optimize=True)
                elif fmt == "BMP":
                    pal.save(out, format="BMP")
                else:
                    pal.save(out, format="TIFF", compression="tiff_lzw")
            else:
                img.save(out, format=fmt, optimize=True)
        elif mode == ImageCompressionMode.lossless:
            if fmt == "PNG":
                img.save(out, format=fmt, optimize=True, compress_level=9)
            elif fmt == "WEBP":
                img.save(out, format=fmt, lossless=True, quality=100, method=6)
            elif fmt == "TIFF":
                img.save(out, format=fmt, compression="tiff_lzw")
            elif fmt == "GIF":
                img.save(out, format=fmt, optimize=True)
            else:
                jpeg_save(out, 95)
        elif mode == ImageCompressionMode.high_quality:
            if fmt == "JPEG":
                jpeg_save(out, 92)
            elif fmt == "WEBP":
                img.save(out, format=fmt, quality=92, method=6)
            elif fmt == "PNG":
                img.save(out, format=fmt, optimize=True, compress_level=7)
            else:
                img.save(out, format=fmt, optimize=True)
        elif mode == ImageCompressionMode.balanced:
            if fmt == "JPEG":
                jpeg_save(out, 86)
            elif fmt == "WEBP":
                img.save(out, format=fmt, quality=82, method=6)
            elif fmt == "PNG":
                img.save(out, format=fmt, optimize=True, compress_level=9)
            else:
                img.save(out, format=fmt, optimize=True)
        else:
            if fmt == "JPEG":
                jpeg_save(out, 80)
            elif fmt == "WEBP":
                img.save(out, format=fmt, quality=75, method=6)
            elif fmt == "PNG":
                img.save(out, format=fmt, optimize=True, compress_level=9)
            else:
                img.save(out, format=fmt, optimize=True)

        result = out.getvalue()

        # For lossy formats, attempt to reach target reduction carefully without over-degrading quality.
        if target_reduction_percent and fmt in {"JPEG", "WEBP"} and level is None:
            target_size = int(len(data) * (1 - target_reduction_percent / 100.0))
            if target_size > 0 and len(result) > target_size:
                stepped = BytesIO()
                qualities = [88, 84, 80, 76]
                for q in qualities:
                    stepped.seek(0)
                    stepped.truncate(0)
                    if fmt == "JPEG":
                        jpeg_save(stepped, q)
                    else:
                        img.save(stepped, format=fmt, quality=q, method=6)
                    candidate = stepped.getvalue()
                    if len(candidate) <= target_size:
                        result = candidate
                        break
                    if len(candidate) < len(result):
                        result = candidate

        if force_reduce_size and len(result) >= len(data) and level is None:
            stepped = BytesIO()
            best = result

            if fmt == "JPEG":
                for q in [78, 72, 66, 60, 54, 48, 42]:
                    stepped.seek(0)
                    stepped.truncate(0)
                    jpeg_save(stepped, q)
                    candidate = stepped.getvalue()
                    if len(candidate) < len(best):
                        best = candidate
                    if len(best) < len(data):
                        break
            elif fmt == "WEBP":
                for q in [75, 68, 60, 52, 45, 38, 32]:
                    stepped.seek(0)
                    stepped.truncate(0)
                    img.save(stepped, format=fmt, quality=q, method=6)
                    candidate = stepped.getvalue()
                    if len(candidate) < len(best):
                        best = candidate
                    if len(best) < len(data):
                        break
            elif fmt == "PNG":
                source_for_palette = img.convert("RGBA") if img.mode in {"RGBA", "LA", "P"} else img.convert("RGB")
                for colors in [192, 160, 128, 96, 64, 48, 32]:
                    stepped.seek(0)
                    stepped.truncate(0)
                    pal = source_for_palette.convert("P", palette=Image.ADAPTIVE, colors=colors)
                    pal.save(stepped, format="PNG", optimize=True, compress_level=9)
                    candidate = stepped.getvalue()
                    if len(candidate) < len(best):
                        best = candidate
                    if len(best) < len(data):
                        break

            result = best

        # Never return a larger file than the input for compression operations.
        # If no meaningful reduction is achieved, keep the original bytes.
        if len(result) >= len(data):
            return data
        return result


def image_media_type(ext: str) -> str:
    normalized = ext.lower().lstrip(".")
    if normalized in {"jpg", "jpeg"}:
        return "image/jpeg"
    if normalized == "png":
        return "image/png"
    if normalized == "webp":
        return "image/webp"
    if normalized == "bmp":
        return "image/bmp"
    if normalized in {"tif", "tiff"}:
        return "image/tiff"
    if normalized == "gif":
        return "image/gif"
    if normalized == "svg":
        return "image/svg+xml"
    return "application/octet-stream"


def images_to_pdf(image_paths: list[Path], output_pdf: Path, options: ImageToPdfOptions) -> Path:
    c = canvas.Canvas(str(output_pdf))

    for path in image_paths:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            w_px, h_px = img.size
            img_reader = ImageReader(img)

            if options.page_size.value == "original":
                page_w, page_h = w_px, h_px
            else:
                page_w, page_h = PAGE_SIZES[options.page_size.value]

            c.setPageSize((page_w, page_h))

            if options.fit_to_page:
                ratio = min(page_w / w_px, page_h / h_px)
                draw_w = w_px * ratio
                draw_h = h_px * ratio
            else:
                draw_w, draw_h = w_px, h_px

            x = (page_w - draw_w) / 2
            y = (page_h - draw_h) / 2
            c.drawImage(img_reader, x, y, draw_w, draw_h, preserveAspectRatio=True)
            c.showPage()

    c.save()
    return output_pdf
