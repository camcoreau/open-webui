# CamCore AI production rollback

`DEPLOYMENT-STATUS.md` records the current verified production image and the
previous verified image. The previous verified image is the rollback point, and
this file must name the same image. The deployment contract workflow fails if
this file, `DEPLOYMENT-STATUS.md`, `README.md` and `compose.yaml` disagree, or
if this file names the image that is currently pinned.

Rollback image (verified 2026-09-13, OPS-430):

`ghcr.io/camcoreau/open-webui:camcore-5c31191973557c9ccb94eb0a211ef004eae572ae@sha256:a8cdb5270ce03cd7abfa27030eedff90bbdfc4ebaef2320a5cb0c8553c059330`

The rollback image differs from the current image only in the runtime patch
layer: it still replays stored reasoning items that lack `encrypted_content`
into stateless Responses requests, and its build predates the tool-server
behaviour test. It carries the same Core Coral branding, the same identity
patch and assets, the same upstream v0.11.1 base, and it runs against the same
`compose.yaml` environment, network, volume and health check. Keep
`OPENAI_API_CONFIGS` and `ENABLE_RESPONSES_API_STATEFUL=false` unchanged when
rolling back to it.

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
