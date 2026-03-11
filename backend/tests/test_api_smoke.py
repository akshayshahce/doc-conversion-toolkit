from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import fitz
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader, PdfWriter

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app.main import app


client = TestClient(app)


def _image_bytes(fmt: str = "PNG", color: tuple[int, int, int] = (120, 90, 200)) -> bytes:
    img = Image.new("RGB", (120, 80), color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _pdf_bytes(page_count: int = 3) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _pdf_with_image_bytes() -> bytes:
    img = Image.new("RGB", (1200, 1200))
    for x in range(1200):
        for y in range(1200):
            img.putpixel((x, y), ((x * 3 + y * 5) % 256, (x * 7 + y * 11) % 256, (x * 13 + y * 17) % 256))
    src = io.BytesIO()
    img.save(src, format="JPEG", quality=95)

    doc = fitz.open()
    page = doc.new_page(width=1200, height=1200)
    page.insert_image(fitz.Rect(0, 0, 1200, 1200), stream=src.getvalue())
    return doc.tobytes()


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_image_convert() -> None:
    data = _image_bytes("PNG")
    response = client.post(
        "/api/images/convert",
        data={"output_format": "jpeg", "background_color": "#ffffff"},
        files=[("files", ("sample.png", data, "image/png"))],
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/octet-stream")


def test_image_compress_weird_filename() -> None:
    data = _image_bytes("PNG")
    response = client.post(
        "/api/images/compress",
        data={"mode": "high_quality", "strip_metadata": "false"},
        files=[("files", ("Screenshot 2026-03-10 at 2.14.32 PM.png", data, "image/png"))],
    )
    assert response.status_code == 200


def test_image_compress_jpeg_without_exif() -> None:
    data = _image_bytes("JPEG")
    response = client.post(
        "/api/images/compress",
        data={"mode": "high_quality", "strip_metadata": "false"},
        files=[("files", ("camera.jpg", data, "image/jpeg"))],
    )
    assert response.status_code == 200


def test_image_compress_never_larger_than_input() -> None:
    img = Image.new("RGB", (320, 320), (120, 80, 60))
    src = io.BytesIO()
    img.save(src, format="JPEG", quality=55)
    source_bytes = src.getvalue()

    response = client.post(
        "/api/images/compress",
        data={"mode": "high_quality", "strip_metadata": "false"},
        files=[("files", ("small.jpg", source_bytes, "image/jpeg"))],
    )
    assert response.status_code == 200
    assert len(response.content) <= len(source_bytes)


def test_image_compress_force_reduce_size() -> None:
    img = Image.new("RGB", (420, 420))
    for x in range(420):
        for y in range(420):
            img.putpixel((x, y), ((x * 7 + y * 3) % 256, (x * 5 + y * 11) % 256, (x * 13 + y * 17) % 256))
    src = io.BytesIO()
    img.save(src, format="JPEG", quality=82, optimize=True)
    source_bytes = src.getvalue()

    response = client.post(
        "/api/images/compress",
        data={"mode": "high_quality", "strip_metadata": "false", "force_reduce_size": "true"},
        files=[("files", ("force.jpg", source_bytes, "image/jpeg"))],
    )
    assert response.status_code == 200
    assert len(response.content) < len(source_bytes)


def test_image_compress_preview_metadata() -> None:
    data = _image_bytes("PNG")
    response = client.post(
        "/api/images/compress-preview",
        data={"mode": "high_quality", "target_reduction_percent": "10", "force_reduce_size": "false"},
        files=[("file", ("preview.png", data, "image/png"))],
    )
    assert response.status_code == 200
    assert response.headers["x-original-size"] == str(len(data))
    assert "x-output-size" in response.headers
    assert "x-reduction-percent" in response.headers
    assert response.headers["content-type"].startswith("image/png")


def test_image_resize() -> None:
    data = _image_bytes("PNG")
    response = client.post(
        "/api/images/resize",
        data={"width": "64", "height": "64", "keep_aspect_ratio": "true"},
        files=[("files", ("sample.png", data, "image/png"))],
    )
    assert response.status_code == 200
    out = Image.open(io.BytesIO(response.content))
    assert out.width <= 64
    assert out.height <= 64


def test_images_to_pdf() -> None:
    i1 = _image_bytes("PNG", (255, 0, 0))
    i2 = _image_bytes("PNG", (0, 255, 0))
    response = client.post(
        "/api/images/to-pdf",
        data={"page_size": "a4", "fit_to_page": "true", "filename": "images.pdf"},
        files=[
            ("files", ("1.png", i1, "image/png")),
            ("files", ("2.png", i2, "image/png")),
        ],
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_pdf_to_images() -> None:
    pdf = _pdf_bytes(2)
    response = client.post(
        "/api/pdf/to-images",
        data={"format": "png", "dpi": "150", "page_range": "1-2"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
        assert len(zf.namelist()) == 2


def test_pdf_to_single_jpeg_image() -> None:
    pdf = _pdf_bytes(1)
    response = client.post(
        "/api/pdf/to-images",
        data={"format": "jpeg", "dpi": "600", "page_range": "1"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/octet-stream")
    img = Image.open(io.BytesIO(response.content))
    assert img.format == "JPEG"


def test_pdf_compress() -> None:
    pdf = _pdf_bytes(2)
    response = client.post(
        "/api/pdf/compress",
        data={"mode": "quality_first"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    assert "x-original-size" in response.headers
    assert "x-output-size" in response.headers


def test_pdf_compress_target_and_force() -> None:
    pdf = _pdf_with_image_bytes()
    response = client.post(
        "/api/pdf/compress",
        data={"mode": "strong", "target_reduction_percent": "20", "force_reduce_size": "true"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    assert len(response.content) <= len(pdf)
    assert response.headers["x-force-reduce-size"] == "true"


def test_pdf_merge() -> None:
    p1 = _pdf_bytes(1)
    p2 = _pdf_bytes(1)
    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("a.pdf", p1, "application/pdf")),
            ("files", ("b.pdf", p2, "application/pdf")),
        ],
    )
    assert response.status_code == 200
    merged = PdfReader(io.BytesIO(response.content))
    assert len(merged.pages) == 2


def test_pdf_split() -> None:
    pdf = _pdf_bytes(4)
    response = client.post(
        "/api/pdf/split",
        data={"ranges": "1-2,3-4"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
        assert len(zf.namelist()) == 2


def test_pdf_extract() -> None:
    pdf = _pdf_bytes(4)
    response = client.post(
        "/api/pdf/extract",
        data={"pages": "2-3"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    out = PdfReader(io.BytesIO(response.content))
    assert len(out.pages) == 2


def test_pdf_rotate() -> None:
    pdf = _pdf_bytes(2)
    response = client.post(
        "/api/pdf/rotate",
        data={"pages": "1", "degrees": "90"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200


def test_pdf_delete() -> None:
    pdf = _pdf_bytes(3)
    response = client.post(
        "/api/pdf/delete",
        data={"pages": "2"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    out = PdfReader(io.BytesIO(response.content))
    assert len(out.pages) == 2


def test_pdf_reorder() -> None:
    pdf = _pdf_bytes(3)
    response = client.post(
        "/api/pdf/reorder",
        data={"order": "3,1,2"},
        files=[("file", ("sample.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    out = PdfReader(io.BytesIO(response.content))
    assert len(out.pages) == 3
