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

# Binary brand assets are staged by the branding workflow from the exact pinned
# camcoreau/camcore-websites commit before this Dockerfile is built.
COPY deploy/camcore/branding/runtime-assets/camcore-logo.png /app/build/static/camcore-logo.png
COPY deploy/camcore/branding/runtime-assets/favicon.png /app/build/static/favicon.png
COPY deploy/camcore/branding/runtime-assets/favicon.png /app/build/static/favicon-96x96.png
COPY deploy/camcore/branding/runtime-assets/favicon.svg /app/build/static/favicon.svg
COPY deploy/camcore/branding/runtime-assets/apple-touch-icon.png /app/build/static/apple-touch-icon.png
COPY deploy/camcore/branding/runtime-assets/icon-512.png /app/build/static/icon-512.png

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
