# CamCore AI production rollback

If an Open WebUI production rollout fails validation, restore the last verified
production image reference in `deploy/camcore/compose.yaml`:

`ghcr.io/camcoreau/open-webui:camcore-97bdadb845fd0f5c39a1c069b29bed8463f23787@sha256:d86d644c8864a82d99201d5a9b3f8c99c33d23d8c2531e5debf3a2d305a157d1`

For the 2026-08-28 Responses migration rollback, also remove
`"api_type":"responses"` from `OPENAI_API_CONFIGS` so the predecessor uses its
verified Chat Completions contract. Keep `ENABLE_RESPONSES_API_STATEFUL=false` (or
remove the variable with the Responses configuration); never enable stateful
Responses while using the verified predecessor.

Before redeploying, preserve a transaction-consistent backup of the persistent
Open WebUI data volume. After redeploy, confirm the immutable image digest,
healthy state, zero unexpected restarts, unchanged volume/network attachment,
no published host ports, Entra-only sign-in, and a successful basic chat.
