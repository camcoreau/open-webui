# Deployment status

Production deployment verified on 2026-09-13 (OPS-430).

Immutable image:
`ghcr.io/camcoreau/open-webui:camcore-5c31191973557c9ccb94eb0a211ef004eae572ae@sha256:a8cdb5270ce03cd7abfa27030eedff90bbdfc4ebaef2320a5cb0c8553c059330`

- Source image build: successful from revision `5c31191973557c9ccb94eb0a211ef004eae572ae` (source change PR #39 — `verify_assets.py` derives `favicon.ico` from the verified CamCore `favicon.png` at image build and fails if the upstream Open WebUI `.ico` would still be served; Dockerfile and workflow guards; `BRANDING.md` "Derived browser icons").
- Production compose pin: merged to `main` at `736e3ac` (PR #40). No environment, network, volume or health-check change; `DEFAULT_LOCALE=en-GB` and the Entra-only guardrail carried forward unchanged.
- Host redeploy: complete through the Git-backed Portainer stack `camcore-open-webui` in environment `7`, stack `67`, at 16:55 AEST (re-pull image and redeploy; stack settings unchanged — reference `refs/heads/main`, git authentication off since OPS-367 because the repository is public; restore a token on the stack if the repository is ever made private).
- Runtime verification: container recreated 2026-09-13 16:55:34 AEST, `healthy` after the start period, restart count 0; `/api/config` reports `name = "Jarvis | CamCore AI"`, `version = "0.11.1"`, `default_locale = "en-GB"`; the root URL still auto-redirects to Microsoft Entra.
- Branding verification: `/static/favicon.ico` now served at 3 329 bytes, sha256 `f4a6d68472cc08e7…` (the CamCore mark; previously the upstream Open WebUI icon at 4 286 bytes, sha256 `cf00f7de…`), `content-type: image/vnd.microsoft.icon`, decodes as a 64×64 image. Unchanged: `/static/custom.css` sha256 `02b7a77a5be4e78c2a807e59d5fa833e1df03ed92ea096809c9cf74e861f1308` (15 302 bytes), `favicon.png` and `favicon-96x96.png` (3 307 bytes), `favicon.svg` (4 539 bytes), `apple-touch-icon.png`, `logo.png`, splash assets and the PWA manifest — all HTTP 200.
- Protected contract: Microsoft Entra-only authentication, the private `npm-backend` network, the persistent data volume, and no published host ports remain unchanged.
- `/static/favicon-dark.png` is not referenced by Open WebUI v0.11.1 or by the CamCore layer and is intentionally not shipped; a 404 for that path is a probe of an unused name, not a gap (OPS-430, `BRANDING.md`).

Previous verified deployment (rollback point): `ghcr.io/camcoreau/open-webui:camcore-1f312b93628d30861b00f7d448c28f8c32a73d9f@sha256:ec71ef7a0ca35cae7a4bf6848f544546c1c741c305474400fc67ccf1630774ac` (verified 2026-09-08, OPS-367) — revert `736e3ac` on `main` and pull-and-redeploy stack 67 to restore it.
