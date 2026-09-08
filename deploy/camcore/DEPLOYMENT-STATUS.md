# Deployment status

Production deployment verified on 2026-09-08 (OPS-367).

Immutable image:
`ghcr.io/camcoreau/open-webui:camcore-1f312b93628d30861b00f7d448c28f8c32a73d9f@sha256:ec71ef7a0ca35cae7a4bf6848f544546c1c741c305474400fc67ccf1630774ac`

- Source image build: successful from revision `1f312b93628d30861b00f7d448c28f8c32a73d9f` (branding workflow run 26; source change PR #36 — Core Coral palette in `custom.css`, workflow palette guards, `BRANDING.md`).
- Production compose pin: merged to `main` at `d14f0e3` (PR #37), together with `DEFAULT_LOCALE=en-GB`.
- Host redeploy: complete through the Git-backed Portainer stack `camcore-open-webui` in environment `7`, stack `67`, at 21:51 AEST. The stack's git authentication was switched off during this change because the stored token had expired; the repository is public, so anonymous clone is used. If the repository is ever made private, a token must be restored on the stack.
- Runtime verification: container recreated 2026-09-08 21:51:57, `healthy` after the start period; `/api/config` reports `name = "Jarvis | CamCore AI"`, `version = "0.11.1"`, `default_locale = "en-GB"`.
- Branding verification: `/static/custom.css` served at sha256 `02b7a77a5be4e78c2a807e59d5fa833e1df03ed92ea096809c9cf74e861f1308` (15 302 bytes) with no retired cyan/blue value present; favicon, touch icon, logo and splash assets unchanged and served with HTTP 200; Entra sign-in and the branded shell confirmed in a browser session.
- Protected contract: Microsoft Entra-only authentication, the private `npm-backend` network, the persistent data volume, and no published host ports remain unchanged.
- Known gap carried forward: `/static/favicon-dark.png` returns 404 (dark-mode tab icon only); tracked in OPS-367.

Previous verified deployment (rollback point): `ghcr.io/camcoreau/open-webui:camcore-a3a424d79ecc8f525215af19eb82c2097cad8b13@sha256:a956985f17f9794d35350a02c7cf6ee83d43b53ab45e2792b320e85ab21fe64b` — revert `d14f0e3` on `main` and pull-and-redeploy stack 67 to restore it.
