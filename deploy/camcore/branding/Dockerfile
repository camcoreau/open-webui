# syntax=docker/dockerfile:1.7

# CamCore visual overlay only. Keep the application runtime pinned to the exact
# upstream Open WebUI image approved by the production deployment.
FROM ghcr.io/open-webui/open-webui:v0.11.0@sha256:72c0ba641ba75e7aa52655cb242570906ececd09b1140fb736483038a22b3228

USER 0

COPY deploy/camcore/branding/custom.css /app/build/static/custom.css
COPY deploy/camcore/branding/loader.js /app/build/static/loader.js
COPY deploy/camcore/branding/camcore-mark.svg /app/build/static/camcore-mark.svg
COPY deploy/camcore/branding/camcore-mark.svg /app/build/static/favicon.svg

RUN test -s /app/build/static/custom.css \
    && test -s /app/build/static/loader.js \
    && test -s /app/build/static/camcore-mark.svg \
    && test -s /app/build/static/favicon.svg

# The base image start-up path copies /app/build/static into the backend static
# directory before serving the app, so no entrypoint or application code change
# is required for the CamCore visual layer.
