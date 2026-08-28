# CamCore AI production rollback

If an Open WebUI production rollout fails validation, restore the last verified
production image reference in `deploy/camcore/compose.yaml`:

`ghcr.io/camcoreau/open-webui:camcore-4d85a50720f227d69c85dc6256fdbdc970ce138a@sha256:cfc5c4e4d63e8779d86d1cc56807555dc42b0d65217af0c6efbd209eaf30ff7d`

For the 2026-08-28 Responses migration rollback, also remove
`"api_type":"responses"` from `OPENAI_API_CONFIGS` so the predecessor uses its
verified Chat Completions contract. Keep `ENABLE_RESPONSES_API_STATEFUL=false` (or
remove the variable with the Responses configuration); never enable stateful
Responses while using the verified predecessor.

Before redeploying, preserve a transaction-consistent backup of the persistent
Open WebUI data volume. After redeploy, confirm the immutable image digest,
healthy state, zero unexpected restarts, unchanged volume/network attachment,
no published host ports, Entra-only sign-in, and a successful basic chat.
