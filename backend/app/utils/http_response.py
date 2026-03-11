from pathlib import Path

from fastapi.responses import Response


def file_bytes_response(path: Path, media_type: str, filename: str, extra_headers: dict[str, str] | None = None) -> Response:
    data = path.read_bytes()
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if extra_headers:
        headers.update(extra_headers)
    return Response(content=data, media_type=media_type, headers=headers)
