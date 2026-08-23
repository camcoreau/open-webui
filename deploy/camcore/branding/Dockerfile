# syntax=docker/dockerfile:1.7

# CamCore presentation and product-identity layer. Keep the application runtime
# pinned to the exact upstream Open WebUI image approved by production.
FROM ghcr.io/open-webui/open-webui:v0.11.0@sha256:72c0ba641ba75e7aa52655cb242570906ececd09b1140fb736483038a22b3228

USER 0

# Text assets are versioned in this repository.
COPY deploy/camcore/branding/custom.css /app/build/static/custom.css
COPY deploy/camcore/branding/loader.js /app/build/static/loader.js
COPY deploy/camcore/branding/camcore-mark.svg /app/build/static/camcore-mark.svg
COPY deploy/camcore/branding/camcore-manifest.json /app/build/static/camcore-manifest.json
COPY deploy/camcore/branding/patch_runtime.py /tmp/camcore-patch-runtime.py

# Use the real production CamCore assets. They are downloaded only while the
# immutable image is built; the running service has no dependency on camcore.au.
# The following Git blob hashes are pinned to camcoreau/camcore-websites commit
# c652985eb0ada755c6a3940da5426d57c59b293a and are verified immediately below.
ADD https://camcore.au/assets/camcore-logo.png /app/build/static/camcore-logo.png
ADD https://camcore.au/assets/favicon.png /app/build/static/favicon.png
ADD https://camcore.au/assets/apple-touch-icon.png /app/build/static/apple-touch-icon.png
ADD https://camcore.au/assets/icon-512.png /app/build/static/icon-512.png

RUN python - <<'PY'
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

expected = {
    Path('/app/build/static/camcore-logo.png'): '8e5f36f6b13021145449ff59cd95593650963921',
    Path('/app/build/static/favicon.png'): '77b25f513e3bd501d6e2578b4c8bee73da0928e8',
    Path('/app/build/static/apple-touch-icon.png'): '5ec9b1ea22bd45c50ff159a5b4046eba424f67b6',
    Path('/app/build/static/icon-512.png'): '540a5b2a15dd3d9f830dd58555f6b653c12c5f29',
}

for path, expected_sha in expected.items():
    data = path.read_bytes()
    git_blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    if git_blob != expected_sha:
        raise SystemExit(
            f'CamCore production asset verification failed for {path}: '
            f'expected {expected_sha}, got {git_blob}'
        )

# Open WebUI ships an SVG favicon link. Generate an SVG wrapper around the exact
# verified CamCore PNG so that link also resolves to the production identity.
favicon = Path('/app/build/static/favicon.png').read_bytes()
encoded = base64.b64encode(favicon).decode('ascii')
Path('/app/build/static/favicon.svg').write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    f'<image width="512" height="512" href="data:image/png;base64,{encoded}"/>'
    '</svg>',
    encoding='utf-8',
)
Path('/app/build/static/favicon-96x96.png').write_bytes(favicon)
PY

# Open WebUI v0.11 appends "(Open WebUI)" to every custom WEBUI_NAME. CamCore's
# <=50-user branding exception permits replacing that deployed product branding.
# The patch is exact-match guarded and fails the image build on upstream drift.
RUN python /tmp/camcore-patch-runtime.py /app/backend/open_webui/env.py \
    && rm -f /tmp/camcore-patch-runtime.py \
    && ! grep -Fq "WEBUI_NAME += ' (Open WebUI)'" /app/backend/open_webui/env.py \
    && grep -Fq "WEBUI_FAVICON_URL = '/static/favicon.png'" /app/backend/open_webui/env.py

RUN test -s /app/build/static/custom.css \
    && test -s /app/build/static/loader.js \
    && test -s /app/build/static/camcore-mark.svg \
    && test -s /app/build/static/camcore-logo.png \
    && test -s /app/build/static/favicon.png \
    && test -s /app/build/static/favicon-96x96.png \
    && test -s /app/build/static/favicon.svg \
    && test -s /app/build/static/apple-touch-icon.png \
    && test -s /app/build/static/icon-512.png \
    && test -s /app/build/static/camcore-manifest.json

# The base image startup path copies /app/build/static into the backend static
# directory before serving the app, so the existing entrypoint remains unchanged.
