# CamCore branding for Open WebUI

The CamCore deployment presents Open WebUI as **Jarvis | CamCore AI** while retaining the upstream Open WebUI attribution required by the bundled licence.

Open WebUI v0.11 appends `(Open WebUI)` automatically when `WEBUI_NAME` is changed from the upstream default, so the deployed title becomes:

```text
Jarvis | CamCore AI (Open WebUI)
```

The bundled Open WebUI licence permits altering or replacing Open WebUI branding for deployments with no more than 50 end users in a rolling 30-day period, or where separate written/enterprise permission exists. Review the licence again before expanding beyond that branding exception.

## CamCore design source

The visual layer deliberately follows the current `camcore.au` design system rather than inventing an unrelated AI theme. Its core production tokens are:

```text
Canvas              #030709
Raised canvas       #071014
Surface             #0b171d
Primary cyan        #16d7e8
Cyan highlight      #98f4fb
Secondary blue      #4aa8ff
Primary text        #f7fbff
Muted text          #9cb1c1
```

The background uses the same dark gradient, subtle 64 px grid and restrained cyan/blue radial glow language as the public CamCore site.

## Branding stages

### Phase 1 — supported instance identity

The production compose sets:

```text
WEBUI_NAME=Jarvis | CamCore AI
```

This changes the browser and application identity while keeping explicit upstream attribution.

### Phase 2 — immutable visual layer

The visual package lives under `deploy/camcore/branding/`:

- `custom.css` maps Open WebUI's neutral palette to the CamCore design system and styles the canvas, raised surfaces, controls, focus states, chat chrome and splash screen.
- `camcore-mark.svg` provides a local CamCore/Jarvis identity asset without an external runtime dependency.
- `loader.js` applies the CamCore browser theme colour and favicon.
- `Dockerfile` layers those files over the exact approved upstream Open WebUI v0.11.0 image digest; it does not replace the upstream application runtime.

The resulting image must be deployed by immutable digest. Production must never use `camcore-current`, `latest` or another mutable tag by itself.

The original public CamCore logo remains maintained in `camcoreau/camcore-websites`. The local SVG mark in this repository is intentionally lightweight for the private AI interface; the colour and spacing system remains aligned with CamCore.au.

## Upgrade rule

When Open WebUI is upgraded:

1. review the new upstream licence and release notes;
2. update the pinned upstream digest in the branding Dockerfile;
3. build and validate the branding layer against the new version;
4. inspect the sign-in page, sidebar, chat composer, dialogs and mobile layout;
5. pin the new branded image digest in the production compose;
6. preserve visible Open WebUI attribution.

Do not make production depend on Portainer temporary Git-checkout bind mounts or public internet assets for branding.
