#!/usr/bin/env python3
"""Verify checked-in CamCore production assets before packaging them.

Hashes are Git blob object IDs for the exact files copied by the branding Dockerfile.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

STATIC_DIR = Path('/app/build/static')

EXPECTED = {
    STATIC_DIR / 'camcore-logo.png': '767a24df671bd80ef7bc4c3c1f8d9e4ad2574c27',
    STATIC_DIR / 'favicon.png': '7b51b31e0f695de172c884b6aed631ba2019ca3e',
    STATIC_DIR / 'apple-touch-icon.png': '82c7bc1f621cdd6a9b396840b7d1a9319d4908b2',
    STATIC_DIR / 'icon-512.png': '0b5c9f8100659df93929db4629593f13347c28c6',
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
