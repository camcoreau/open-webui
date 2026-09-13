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

Open WebUI v0.11.1 automatically appends `(Open WebUI)` to every non-default `WEBUI_NAME`. The CamCore branded image applies a deliberately narrow, exact-match build-time patch to `backend/open_webui/env.py` so the deployed name remains `Jarvis | CamCore AI` and the application favicon points to the local CamCore asset.

`patch_runtime.py` is fail-closed and preserves the upstream licence notices surrounding both identity settings. If the upstream identity block changes, the image build fails and the patch must be reviewed against the new upstream release before deployment.

The branding base is pinned to released Open WebUI tag `v0.11.1`, source revision `d3e8bf3405e848cfba377814d0aa7ba7290e414d`, and GHCR index digest:

```text
sha256:6bb1fbe8ab0a3e0456067f493044ffb66a30a65a34be47f6a5862176a370dd16
```

## CamCore design source

The visual layer follows the production `camcore.au` design system rather than defining a separate AI theme. Core tokens include:

```text
Canvas              #02070a
Raised canvas       #040b10
Surface             #07131a
Core Coral          #ff4b2b   primary accent
Coral highlight     #ff7457
Coral soft          #ff9a7f   secondary accent
Accent ink          #001215   text on coral fills
Line                #4a2a24
Line, strong        #8e4637
Success             #5ee39c
Warning             #ffc967
Error               #ff8298
Primary text        #f4f8fa
Soft text           #d2c5c1
Muted text          #bca9a4
Quiet text          #a78d86
Focus               #ffb09d
```

These are the production `camcore.au` tokens as at 8 September 2026 (CamCore Complete Brand Pack: Core Coral `#FF4B2B`, Deep Core `#101720`). The earlier cyan/blue generation (`#16d7e8`, `#98f4fb`, `#4aa8ff`, `#adf7ff`, canvas `#030709`/`#071014`) is retired; the branding workflow fails the build if any of those values reappear in `custom.css` (OPS-367). The neutral ramp values not published by the site (`#ece7e5`, `#8a746e`, `#6b5852`) are interpolated between published text tokens.

The application uses the same dark gradient, 64 px grid, restrained coral radial glow, raised glass surfaces, border language, focus treatment and radius scale as the public CamCore site.

## Production assets

The approved CamCore identity assets are checked into deploy/camcore/branding/ and copied directly into the immutable image. This keeps the branding source reviewable and prevents the image build from depending on the deployment timing or availability of camcore.au.

The build verifies each file's Git blob hash before continuing:

| Asset                | Git blob SHA                             |
| -------------------- | ---------------------------------------- |
| camcore-logo.png     | 767a24df671bd80ef7bc4c3c1f8d9e4ad2574c27 |
| favicon.png          | 7b51b31e0f695de172c884b6aed631ba2019ca3e |
| apple-touch-icon.png | 82c7bc1f621cdd6a9b396840b7d1a9319d4908b2 |
| icon-512.png         | 0b5c9f8100659df93929db4629593f13347c28c6 |

A missing or unexpected asset causes the image build to fail. The running container has no external branding-asset dependency.

### Derived browser icons

Open WebUI v0.11.1's `app.html` links four icon paths in the initial HTML — `/static/favicon.png`, `/static/favicon-96x96.png`, `/static/favicon.svg` and `/static/favicon.ico` (shortcut icon) — before `loader.js` runs and repoints them. So that none of those requests can ever return an upstream Open WebUI icon, `verify_assets.py` derives the other three from the verified `favicon.png` at image build time: `favicon.svg` (the PNG wrapped in an SVG `<image>`), `favicon-96x96.png` (a byte copy) and `favicon.ico` (a single-entry ICO container holding the PNG verbatim). The build fails if the upstream `favicon.ico` (sha256 `cf00f7de3ac614f87e58450cf7b832dcb3b1e0cf2ef562c1b4e71cc7b987f408`) is still what would be served (OPS-430).

The 64 px `favicon.png` is an opaque Deep Core tile carrying the white and Core Coral mark, so it reads the same on light and dark browser chrome. Open WebUI v0.11.1 does not reference a `favicon-dark.png` anywhere (`app.html`, `+layout.svelte`, upstream `static/`), and none is shipped; a `404` for that path is a probe of an unused name, not a gap (OPS-430).

## Branding package

The visual package lives under `deploy/camcore/branding/`:

- `custom.css` implements the managed CamCore dark visual system across the application shell, sidebar, chat composer, markdown/code surfaces, dialogs, menus, toasts, sign-in fallback and splash screen.
- `loader.js` applies the CamCore browser identity, managed dark theme, title normalisation, favicon/touch icon metadata and PWA manifest.
- `camcore-manifest.json` gives installed/home-screen instances the `Jarvis | CamCore AI` name and CamCore application colours.
- `patch_runtime.py` removes only Open WebUI v0.11.1's automatic custom-name suffix, preserves the surrounding upstream licence notices and points the runtime favicon setting to the bundled local CamCore favicon.
- `test_patch_runtime.py` verifies that the guarded patch changes only the reviewed identity block and retains both upstream licence notices.
- `camcore-mark.svg` is the scalable local connected-core wordmark; raster copies beside it supply browser, touch, and installed-app surfaces.
- `Dockerfile` layers all branding over the exact approved Open WebUI v0.11.1 image digest.

## Experience contract

A branded release is acceptable only when all of the following are true:

1. browser title and installed-app name show `Jarvis | CamCore AI`;
2. favicon (`.png`, `.svg`, `.ico` and the 96 px PNG), touch icon, sidebar mark, auth fallback and splash use CamCore identity assets;
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
5. regenerate the checked-in CamCore assets and re-pin their verified blob hashes;
6. build and validate the branding layer against the new version;
7. inspect sign-in, sidebar, chat composer, markdown/code rendering, dialogs, PWA metadata and mobile layout;
8. pin the new branded image digest in production only after those checks pass.

The branding workflow extracts its identity, OpenAPI-tool and Responses compatibility fixtures from the exact Dockerfile-pinned upstream image. The repository checkout is not used as a substitute for the runtime being patched; the final image build remains the fail-closed compatibility gate.

Do not make production depend on temporary Git checkouts, mutable image tags or public runtime branding assets.
