from enum import Enum

from pydantic import BaseModel, Field


class PdfImageFormat(str, Enum):
    png = "png"
    jpeg = "jpeg"
    webp = "webp"


class PdfCompressionMode(str, Enum):
    quality_first = "quality_first"
    light = "light"
    balanced = "balanced"
    strong = "strong"


class PdfToImageOptions(BaseModel):
    format: PdfImageFormat = PdfImageFormat.png
    dpi: int = Field(default=300, ge=72, le=600)
    page_range: str | None = None


class PdfCompressionOptions(BaseModel):
    mode: PdfCompressionMode = PdfCompressionMode.quality_first
    filename: str = "compressed.pdf"


class PdfSplitOptions(BaseModel):
    ranges: str = Field(description="Comma-separated ranges like 1-3,5,8-10")


class PdfRotateOptions(BaseModel):
    pages: str = Field(description="Page range, e.g. 1-2,6")
    degrees: int = Field(default=90)


class PdfDeleteOptions(BaseModel):
    pages: str


class PdfExtractOptions(BaseModel):
    pages: str


class PdfReorderOptions(BaseModel):
    order: list[int]
