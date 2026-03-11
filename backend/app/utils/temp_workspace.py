from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.app.core.config import settings


@contextmanager
def workspace() -> Iterator[Path]:
    with TemporaryDirectory(prefix=settings.temp_prefix) as tmp:
        yield Path(tmp)
