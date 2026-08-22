# CamCore branding for Open WebUI

The CamCore deployment presents Open WebUI as **Jarvis | CamCore AI** while retaining the upstream Open WebUI attribution required by the bundled licence.

Open WebUI v0.11 appends `(Open WebUI)` automatically when `WEBUI_NAME` is changed from the upstream default, so the deployed title becomes:

```text
Jarvis | CamCore AI (Open WebUI)
```

The bundled Open WebUI licence permits altering or replacing Open WebUI branding for deployments with no more than 50 end users in a rolling 30-day period, or where separate written/enterprise permission exists. Review the licence again before expanding beyond that branding exception.

## Branding stages

### Phase 1 — supported instance identity

The production compose sets:

```text
WEBUI_NAME=Jarvis | CamCore AI
```

This changes the browser and application identity without modifying the upstream application image.

### Phase 2 — visual CamCore assets

Logo, favicon, splash-screen and CSS customisation should be delivered as an immutable CamCore image layer based on the currently approved upstream Open WebUI image. Do not rely on Portainer temporary Git-checkout bind mounts for production branding assets.

The approved CamCore source assets are maintained in `camcoreau/camcore-websites`, including the public CamCore logo and favicon. Any branded image must continue to preserve visible Open WebUI attribution in accordance with the applicable licence.
