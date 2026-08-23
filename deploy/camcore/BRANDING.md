# CamCore branding for Open WebUI

CamCore deploys Open WebUI as **Jarvis | CamCore AI**: a private AI workspace that follows the same visual and identity system as the rest of CamCore while retaining the upstream software licence, copyright and repository provenance.

## Licence boundary

The bundled Open WebUI licence permits altering, removing or replacing Open WebUI branding when the deployment has no more than 50 end users in any rolling 30-day period, or when separate written/enterprise permission permits it.

The full CamCore product-identity layer in this directory must therefore be deployed only while that exception applies or separate permission exists. If CamCore exceeds that boundary, review the then-current upstream licence before the next deployment and restore any branding required by that licence unless separate permission has been obtained.

Rebranding the deployed product does **not** remove or rewrite the upstream licence, copyright notices, source provenance, SBOM or image ancestry.

## Product identity

The intended user-facing identity is:

```text
Jarvis | CamCore AI
```

Open WebUI v0.11.0 automatically appends `(Open WebUI)` to every non-default `WEBUI_NAME`. The CamCore branded image applies a deliberately narrow, exact-match build-time patch to `backend/open_webui/env.py` so the deployed name remains `Jarvis | CamCore AI` and the application favicon points to the local CamCore asset.

`patch_runtime.py` is fail-closed. If the upstream identity block changes, the image build fails and the patch must be reviewed against the new upstream release before deployment.

## CamCore design source

The visual layer follows the production `camcore.au` design system rather than defining a separate AI theme. Core tokens include:

```text
Canvas              #030709
Raised canvas       #071014
Surface             #0b171d
Primary cyan        #16d7e8
Cyan highlight      #98f4fb
Secondary blue      #4aa8ff
Success             #5ee39c
Warning             #ffc967
Error               #ff8298
Primary text        #f7fbff
Muted text          #9cb1c1
Focus                #adf7ff
```

The application uses the same dark gradient, 64 px grid, restrained cyan/blue radial glow, raised glass surfaces, border language, focus treatment and radius scale as the public CamCore site.

## Production assets

The real CamCore production identity assets remain source-controlled in `camcoreau/camcore-websites`.

The branded image is pinned to CamCore website source revision:

```text
c652985eb0ada755c6a3940da5426d57c59b293a
```

The Docker build downloads the public production copies from `camcore.au` **only during image construction** and verifies their Git blob hashes against that source revision before the build can continue:

| Asset | Git blob SHA |
| --- | --- |
| `camcore-logo.png` | `8e5f36f6b13021145449ff59cd95593650963921` |
| `favicon.png` | `77b25f513e3bd501d6e2578b4c8bee73da0928e8` |
| `apple-touch-icon.png` | `5ec9b1ea22bd45c50ff159a5b4046eba424f67b6` |
| `icon-512.png` | `540a5b2a15dd3d9f830dd58555f6b653c12c5f29` |

A changed, unavailable or unexpected asset causes the image build to fail. The running Open WebUI container has no dependency on `camcore.au` for branding assets.

## Branding package

The visual package lives under `deploy/camcore/branding/`:

- `custom.css` implements the managed CamCore dark visual system across the application shell, sidebar, chat composer, markdown/code surfaces, dialogs, menus, toasts, sign-in fallback and splash screen.
- `loader.js` applies the CamCore browser identity, managed dark theme, title normalisation, favicon/touch icon metadata and PWA manifest.
- `camcore-manifest.json` gives installed/home-screen instances the `Jarvis | CamCore AI` name and CamCore application colours.
- `patch_runtime.py` removes only Open WebUI v0.11.0's automatic custom-name suffix and points the runtime favicon setting to the bundled local CamCore favicon.
- `camcore-mark.svg` remains as a lightweight local fallback/reference mark; the primary visible identity uses the verified production CamCore assets.
- `Dockerfile` layers all branding over the exact approved Open WebUI v0.11.0 image digest.

## Experience contract

A branded release is acceptable only when all of the following are true:

1. browser title and installed-app name show `Jarvis | CamCore AI`;
2. favicon, touch icon, sidebar mark, auth fallback and splash use CamCore identity assets;
3. the app remains a managed dark experience matching the production CamCore palette;
4. sidebar, composer, dialogs, menus, toasts, markdown, code and responsive layouts remain legible and usable;
5. keyboard focus remains clearly visible and reduced-motion preferences are respected;
6. Microsoft Entra authentication, Ollama connectivity, application roles, networking, persistent data and security hardening are unchanged by the branding image;
7. upstream Open WebUI licence and provenance remain bundled and unmodified.

## Release and deployment sequence

Branding source and production deployment are intentionally separate steps:

1. merge the reviewed branding-source change;
2. let the branding workflow build and publish the new amd64 GHCR image;
3. take the immutable `sha256:` image digest published by the workflow;
4. create a separate production deployment change that pins that exact digest in `deploy/camcore/compose.yaml`;
5. deploy through the normal CamCore stack process;
6. validate desktop and mobile splash, Entra sign-in, sidebar, new-chat state, composer, response rendering, dialogs and installed-app metadata;
7. keep the previously approved digest available for immediate rollback.

Production must never use `camcore-current`, `latest` or another mutable tag by itself.

## Upgrade rule

When Open WebUI is upgraded:

1. review the new upstream licence and release notes;
2. confirm the CamCore deployment is still permitted to use full replacement branding;
3. update the pinned upstream image digest in the branding Dockerfile;
4. review `patch_runtime.py` against the new upstream identity implementation;
5. re-pin and verify the current production CamCore asset revision and blob hashes;
6. build and validate the branding layer against the new version;
7. inspect sign-in, sidebar, chat composer, markdown/code rendering, dialogs, PWA metadata and mobile layout;
8. pin the new branded image digest in production only after those checks pass.

Do not make production depend on temporary Git checkouts, mutable image tags or public runtime branding assets.
