# Deployment status

Production pin updated on 2026-09-20; the host redeploy and runtime verification
are pending. This file records the pin at merge time so the deployment contract
check keeps `compose.yaml`, `README.md`, `ROLLBACK.md` and this file in
agreement, and it is updated again once the host redeploy is verified.

Immutable image:
`ghcr.io/camcoreau/open-webui:camcore-7639dc5896eaa56f011ea069ec425af7e0950f45@sha256:4b28ff432592d7340557acdd000ae86e756a58cbb00978498453b928183d1aba`

- Source image build: successful from revision `7639dc5896eaa56f011ea069ec425af7e0950f45` (branding workflow run `35509266063`; source changes PR #42 and PR #43 — `patch_openai_responses.py` no longer replays stored reasoning items that lack `encrypted_content` into stateless Responses requests; `test_patch_tool_servers.py` exercises the OpenAPI tool-server patch against the pinned v0.11.1 fixtures; Dockerfile and workflow guards for both; the `0468f881` release notes retired). The visual layer, identity patch, assets and upstream v0.11.1 base are unchanged from the previous image.
- Production compose pin: this change. No environment, network, volume or health-check change.
- Host redeploy: pending — pull and redeploy the Git-backed Portainer stack `camcore-open-webui` in environment `7`, stack `67`, with stack settings unchanged.
- Runtime verification: pending — container `healthy` after the start period with restart count 0; `/api/config` reports `name = "Jarvis | CamCore AI"`, `version = "0.11.1"` and `default_locale = "en-GB"`; the root URL auto-redirects to Microsoft Entra; a basic chat and one CamCore Operations call complete; a chat recorded before 2026-08-29 that carries reasoning continues without a provider rejection.
- Protected contract: Microsoft Entra-only authentication, the private `npm-backend` network, the persistent data volume, and no published host ports remain unchanged.

Previous verified deployment (rollback point): `ghcr.io/camcoreau/open-webui:camcore-5c31191973557c9ccb94eb0a211ef004eae572ae@sha256:a8cdb5270ce03cd7abfa27030eedff90bbdfc4ebaef2320a5cb0c8553c059330` (verified 2026-09-13, OPS-430) — revert this compose pin commit on `main` and pull-and-redeploy stack 67 to restore it.
