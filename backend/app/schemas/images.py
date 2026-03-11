from enum import Enum

from pydantic import BaseModel, Field


class ImageFormat(str, Enum):
    png = "png"
    jpg = "jpg"
    jpeg = "jpeg"
    webp = "webp"
    bmp = "bmp"
    tiff = "tiff"
    gif = "gif"
    svg = "svg"


class ImageCompressionMode(str, Enum):
    lossless = "lossless"
    high_quality = "high_quality"
    balanced = "balanced"
    maximum = "maximum"


class PdfPageSize(str, Enum):
    original = "original"
    a4 = "a4"
    letter = "letter"


class ImageConvertOptions(BaseModel):
    output_format: ImageFormat
    background_color: str = Field(default="#FFFFFF")


class ImageCompressionOptions(BaseModel):
    mode: ImageCompressionMode = ImageCompressionMode.high_quality
    target_reduction_percent: int | None = Field(default=None, ge=1, le=90)
    strip_metadata: bool = False


class ImageToPdfOptions(BaseModel):
    page_size: PdfPageSize = PdfPageSize.original
    fit_to_page: bool = True
    filename: str = "images.pdf"
