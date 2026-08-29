# Deployment status

Production deployment verified on 2026-08-29.

Immutable image:
`ghcr.io/camcoreau/open-webui:camcore-97bdadb845fd0f5c39a1c069b29bed8463f23787@sha256:d86d644c8864a82d99201d5a9b3f8c99c33d23d8c2531e5debf3a2d305a157d1`

- Source image build: successful from revision `97bdadb845fd0f5c39a1c069b29bed8463f23787`.
- Production compose pin: merged to `main` at `130832ea4073daf707430e51c0163b013353ca41`.
- Host redeploy: complete through the Git-backed Portainer stack `camcore-open-webui` in environment `7`, stack `67`.
- Runtime verification: container healthy with zero restarts, `/health` and `/ready` returning HTTP 200, and Open WebUI reporting version `0.11.1`.
- Live acceptance: ordinary streaming, default-reasoning tools, medium-reasoning tool continuation with persisted history, two sequential tool continuations, reload persistence, and a post-restart continuation all passed.
- Protected contract: Microsoft Entra-only authentication, CamCore branding, the private `npm-backend` network, the persistent data volume, and no published host ports remain unchanged.
