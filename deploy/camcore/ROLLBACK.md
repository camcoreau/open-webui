# CamCore AI production rollback

`DEPLOYMENT-STATUS.md` records the current verified production image and the
previous verified image. The previous verified image is the rollback point, and
this file must name the same image. The deployment contract workflow fails if
this file, `DEPLOYMENT-STATUS.md`, `README.md` and `compose.yaml` disagree, or
if this file names the image that is currently pinned.

Rollback image (verified 2026-09-08, OPS-367):

`ghcr.io/camcoreau/open-webui:camcore-1f312b93628d30861b00f7d448c28f8c32a73d9f@sha256:ec71ef7a0ca35cae7a4bf6848f544546c1c741c305474400fc67ccf1630774ac`

The rollback image differs from the current image only in the derived
`favicon.ico` (OPS-430). It carries the same Core Coral branding and the same
guarded identity, OpenAPI tool-server and stateless Responses patches, and it
runs against the same `compose.yaml` environment, network, volume and health
check. Keep `OPENAI_API_CONFIGS` and `ENABLE_RESPONSES_API_STATEFUL=false`
unchanged when rolling back to it.

## Procedure

1. Preserve a transaction-consistent backup of the `camcore-open-webui-data`
   volume before redeploying.
2. On `main`, revert the most recent compose pin commit (the commit that changed
   the `image:` line of `deploy/camcore/compose.yaml`) so the file pins the
   rollback image above, and merge it through the normal pull-request path.
   Editing the `image:` line to the rollback reference is equivalent.
3. In Portainer environment `7`, pull and redeploy stack `67`
   (`camcore-open-webui`) with the stack settings unchanged.
4. Confirm the running image digest matches the rollback reference, the
   container is `healthy` with zero unexpected restarts, the volume and
   `npm-backend` attachment are unchanged, no host port is published, sign-in is
   Entra-only, and a basic chat plus one CamCore Operations tool call complete.
5. Record the trigger, cause, actions and validation in the YouTrack issue, then
   update `DEPLOYMENT-STATUS.md` so the rollback point moves with it.

A rollback to an image older than the one named above is a fresh deployment
change, not a rollback: review the compose history for that pin first, because
older images required different `OPENAI_API_CONFIGS` and Responses settings.
