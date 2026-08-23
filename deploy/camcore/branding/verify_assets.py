#!/usr/bin/env python3
"""Verify downloaded CamCore production assets before packaging them.

Hashes are Git blob object IDs from camcoreau/camcore-websites at the source
revision documented in BRANDING.md and the branding Dockerfile.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

STATIC_DIR = Path('/app/build/static')

EXPECTED = {
    STATIC_DIR / 'camcore-logo.png': '8e5f36f6b13021145449ff59cd95593650963921',
    STATIC_DIR / 'favicon.png': '77b25f513e3bd501d6e2578b4c8bee73da0928e8',
    STATIC_DIR / 'apple-touch-icon.png': '5ec9b1ea22bd45c50ff159a5b4046eba424f67b6',
    STATIC_DIR / 'icon-512.png': '540a5b2a15dd3d9f830dd58555f6b653c12c5f29',
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def main() -> None:
    for path, expected_sha in EXPECTED.items():
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f'CamCore production asset is missing or empty: {path}')

        data = path.read_bytes()
        actual_sha = git_blob_sha(data)
        if actual_sha != expected_sha:
            raise SystemExit(
                f'CamCore production asset verification failed for {path}: '
                f'expected {expected_sha}, got {actual_sha}'
            )

    favicon = (STATIC_DIR / 'favicon.png').read_bytes()
    encoded = base64.b64encode(favicon).decode('ascii')
    (STATIC_DIR / 'favicon.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<image width="64" height="64" href="data:image/png;base64,{encoded}"/>'
        '</svg>',
        encoding='utf-8',
    )

    # Open WebUI's stock app shell also requests this legacy path before the
    # CamCore loader normalises all icon links. A verified CamCore PNG is used
    # so no upstream favicon flashes during initial paint.
    (STATIC_DIR / 'favicon-96x96.png').write_bytes(favicon)


if __name__ == '__main__':
    main()
