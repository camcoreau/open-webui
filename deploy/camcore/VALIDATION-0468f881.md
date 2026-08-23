# Post-deployment validation

Validate the following after redeploying Jarvis | CamCore AI:

- `https://ai.camcore.network` loads successfully and health checks remain healthy.
- Microsoft Entra authentication redirects and returns successfully.
- Browser title is `Jarvis | CamCore AI` without an appended Open WebUI suffix.
- CamCore favicon, splash identity and dark visual system are visible.
- Sidebar, new-chat screen, composer, Markdown/code content, dialogs and toasts use the CamCore visual layer.
- Mobile layout remains usable.
- Existing `camcore-open-webui-data`, `npm-backend` and `camcore-ai-backend` integration remain intact.

Rollback to the previous pinned image if authentication, health or core chat functionality regresses.
