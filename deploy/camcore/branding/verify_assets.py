#!/usr/bin/env python3
"""Verify checked-in CamCore production assets before packaging them.

Hashes are Git blob object IDs for the exact files copied by the branding Dockerfile.

The verified 64x64 CamCore favicon.png is also the single source for every other
browser icon path that Open WebUI's stock app shell requests before loader.js
runs: favicon.svg, favicon-96x96.png and favicon.ico are derived from it here so
that no upstream Open WebUI icon is ever served from this image (OPS-367, OPS-430).
"""

from __future__ import annotations

import base64
import hashlib
import struct
from pathlib import Path

STATIC_DIR = Path('/app/build/static')

EXPECTED = {
    STATIC_DIR / 'camcore-logo.png': '767a24df671bd80ef7bc4c3c1f8d9e4ad2574c27',
    STATIC_DIR / 'favicon.png': '7b51b31e0f695de172c884b6aed631ba2019ca3e',
    STATIC_DIR / 'apple-touch-icon.png': '82c7bc1f621cdd6a9b396840b7d1a9319d4908b2',
    STATIC_DIR / 'icon-512.png': '0b5c9f8100659df93929db4629593f13347c28c6',
}

# sha256 of static/favicon.ico shipped by upstream Open WebUI v0.11.1. The build
# must never leave this file in place: app.html links it as the shortcut icon in
# the initial HTML, before loader.js repoints the icon links (OPS-430).
UPSTREAM_FAVICON_ICO_SHA256 = 'cf00f7de3ac614f87e58450cf7b832dcb3b1e0cf2ef562c1b4e71cc7b987f408'

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
ICO_HEADER_SIZE = 6
ICO_DIRECTORY_ENTRY_SIZE = 16


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def png_dimensions(png: bytes) -> tuple[int, int]:
    if not png.startswith(PNG_SIGNATURE) or png[12:16] != b'IHDR':
        raise SystemExit('CamCore favicon.png is not a PNG file')
    width, height = struct.unpack('>II', png[16:24])
    return width, height


def build_ico(png: bytes) -> bytes:
    """Wrap one PNG in a single-entry ICO container.

    PNG-compressed ICO entries are supported by every current browser and by
    Windows Vista and later. Keeping the PNG bytes verbatim means the .ico shows
    exactly the verified CamCore mark, with no re-encoding and no extra tooling.
    """
    width, height = png_dimensions(png)
    if width != height or not 16 <= width <= 256:
        raise SystemExit(f'CamCore favicon.png must be square and 16-256 px, got {width}x{height}')

    # ICONDIR: reserved, type (1 = icon), image count.
    header = struct.pack('<HHH', 0, 1, 1)
    # ICONDIRENTRY: width, height (0 encodes 256), palette size, reserved,
    # colour planes, bits per pixel, image size, image offset.
    entry = struct.pack(
        '<BBBBHHII',
        width % 256,
        height % 256,
        0,
        0,
        1,
        32,
        len(png),
        ICO_HEADER_SIZE + ICO_DIRECTORY_ENTRY_SIZE,
    )
    return header + entry + png


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

    # app.html links /static/favicon.ico as the shortcut icon in the initial
    # HTML. Replace the upstream Open WebUI .ico with the CamCore mark and fail
    # the build if the upstream file is somehow still what would be served.
    ico_path = STATIC_DIR / 'favicon.ico'
    ico = build_ico(favicon)
    ico_path.write_bytes(ico)

    written = ico_path.read_bytes()
    if len(written) != ICO_HEADER_SIZE + ICO_DIRECTORY_ENTRY_SIZE + len(favicon):
        raise SystemExit('CamCore favicon.ico was not written completely')
    if written[:ICO_HEADER_SIZE] != struct.pack('<HHH', 0, 1, 1):
        raise SystemExit('CamCore favicon.ico header is invalid')
    if hashlib.sha256(written).hexdigest() == UPSTREAM_FAVICON_ICO_SHA256:
        raise SystemExit('Upstream Open WebUI favicon.ico is still in place')


if __name__ == '__main__':
    main()
