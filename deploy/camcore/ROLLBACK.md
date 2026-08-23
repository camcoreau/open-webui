# CamCore AI branding rollback

If the full branding rollout fails validation, restore the previous known-good production image reference in `deploy/camcore/compose.yaml`:

`ghcr.io/camcoreau/open-webui:camcore-9793564487afccce757ff1bd42f947ca3f67f227@sha256:451b99a261ccc3765541483a48c2a83ca841b4025dcb37fa00bc120d0a4b6e72`

Redeploy the stack and confirm health before investigating the failed release.
