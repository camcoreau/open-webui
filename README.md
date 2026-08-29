# Jarvis | CamCore AI

[![Validate CamCore deployment](https://github.com/camcoreau/open-webui/actions/workflows/camcore-deployment.yml/badge.svg?branch=main)](https://github.com/camcoreau/open-webui/actions/workflows/camcore-deployment.yml)
[![Build CamCore branding image](https://github.com/camcoreau/open-webui/actions/workflows/camcore-branding-image.yml/badge.svg?branch=main)](https://github.com/camcoreau/open-webui/actions/workflows/camcore-branding-image.yml)

**Private AI workspace for CamCore – Cameron Family Secure Network, maintained as a downstream of [Open WebUI](https://github.com/open-webui/open-webui).**

> **CamCore is a privately owned and operated family technology network that delivers secure, reliable and professionally managed digital services for the Cameron household, Cameron-Media and associated family operations.**

**Built for Home. Engineered Like Enterprise.**

This public repository is the source of truth for CamCore's Open WebUI downstream, including the production deployment overlay, CamCore identity layer, validation controls, release process and rollback guidance.

> **Repository status:** `main` records the reviewed source and desired production contract. A merge does not by itself prove that an image was published, a host was redeployed or the live service was verified. Treat those as separate release states, and never commit credentials or private operational data.

## Service identity

| Item              | CamCore contract                                                                               |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| Product           | **Jarvis \| CamCore AI**                                                                       |
| Purpose           | Private AI assistance for CamCore services, infrastructure and productivity                    |
| Private service   | `https://ai.camcore.network`                                                                   |
| Access            | CamCore LAN, authorised NetBird access or another explicitly approved private path             |
| Authentication    | Microsoft Entra single sign-on with `CamCore.AI.User` and `CamCore.AI.Admin` application roles |
| Inference         | Server-managed OpenAI Chat Completions connection                                              |
| Operations tools  | Separate, private and read-only CamCore Operations Gateway                                     |
| Upstream          | [Open WebUI](https://github.com/open-webui/open-webui)                                         |
| Production source | [`deploy/camcore/compose.yaml`](deploy/camcore/compose.yaml)                                   |

The table describes the repository contract. Confirm the live route, running image digest, integrations and acceptance checks separately after every deployment.

## CamCore operating model

The CamCore production profile deliberately narrows the much broader upstream Open WebUI feature set:

- Microsoft Entra is the only sign-in path; local signup and password authentication are disabled.
- OpenAI is the production inference provider through Chat Completions. Local Ollama inference is disabled.
- CamCore Operations is supplied by the standalone `camcoreau/camcore-ai-gateway` service, not by the legacy OpenJarvis runtime.
- The approved Operations surface is read-only and bounded. Modifying infrastructure actions require a separately designed confirmation and audit boundary before they can be enabled.
- Production configuration is controlled by Git and the Portainer stack environment. Admin-panel changes are intentionally non-persistent.
- The service remains private, publishes no host port and runs as a single replica with persistent SQLite data.

This deployment is not an offline or fully local AI stack. Runtime downloads and update checks are suppressed, while approved connections to Microsoft Entra, OpenAI and the private CamCore Operations Gateway remain required.

Generic upstream `pip`, Docker and Ollama quick starts are useful for upstream evaluation, but they are not supported CamCore production instructions. Use the [CamCore deployment runbook](deploy/camcore/README.md) for the managed service and the [upstream documentation](https://docs.openwebui.com/) for general Open WebUI use.

Responses mode is temporarily disabled after live acceptance rejected the previous migration. Do not re-enable it until ordinary streaming and the complete reasoning-plus-tool continuation have both passed live validation.

## Production architecture

```text
Authorised user
      |
      | Microsoft Entra sign-in
      v
Private HTTPS route: ai.camcore.network
      |
      v
Nginx Proxy Manager on npm-backend
      |
      v
Jarvis | CamCore AI
      |-- HTTPS --> OpenAI Chat Completions API
      `-- HTTPS --> ai-tools.camcore.network --> CamCore Operations Gateway
```

Open WebUI joins only `npm-backend`. The Operations Gateway is deployed independently, publishes no host port and shares the dedicated `camcore-ai-operations` network only with Nginx Proxy Manager. Open WebUI, Ollama, OpenJarvis and unrelated containers must not join that gateway network.

## Security posture

The production contract enforces these boundaries:

- the image is pinned by immutable tag and `sha256` digest;
- all Linux capabilities are dropped and `no-new-privileges`, a PID limit, bounded temporary storage, health checks and rotated logs are enabled;
- Entra application assignment and CamCore application roles are the admission boundary;
- administrator access control remains enforced even though provider-model access is intentionally granted to admitted users;
- provider, gateway, OAuth and encryption secrets stay server-side in Portainer or the approved secret store;
- tool-server TLS certificate verification remains enabled;
- plugins, package installation, user API keys, direct connections, terminal servers, code execution, web retrieval, uploads, public sharing and other unapproved extension surfaces remain disabled; and
- audit output records metadata rather than prompt or response bodies.

On a new or reset data volume, the first OAuth user is promoted to administrator by the pinned upstream runtime. Assign only the designated bootstrap operator to `CamCore.AI.Admin` and complete that login first. Verify the administrator, complete a second emergency-administrator login, and only then assign ordinary members.

Copy required variable names from [`deploy/camcore/.env.example`](deploy/camcore/.env.example). Never commit populated values. Generate independent high-entropy credentials, keep stable encryption keys across restarts and trust only the exact `npm-backend` subnet rather than `*` or `0.0.0.0/0`.

## Repository map

| Path                                                                                           | Purpose                                                                          |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [`deploy/camcore/compose.yaml`](deploy/camcore/compose.yaml)                                   | Authoritative production service, image, network, identity and security contract |
| [`deploy/camcore/.env.example`](deploy/camcore/.env.example)                                   | Required Portainer input names without secret values                             |
| [`deploy/camcore/README.md`](deploy/camcore/README.md)                                         | Deployment, Entra, networking, provider, gateway and acceptance runbook          |
| [`deploy/camcore/BRANDING.md`](deploy/camcore/BRANDING.md)                                     | CamCore identity, upstream compatibility, licence boundary and upgrade process   |
| [`deploy/camcore/branding/`](deploy/camcore/branding/)                                         | Fail-closed visual, tool-server and runtime compatibility layer                  |
| [`deploy/camcore/ROLLBACK.md`](deploy/camcore/ROLLBACK.md)                                     | Current production rollback contract                                             |
| [`.github/workflows/camcore-deployment.yml`](.github/workflows/camcore-deployment.yml)         | Production Compose and security-contract validation                              |
| [`.github/workflows/camcore-branding-image.yml`](.github/workflows/camcore-branding-image.yml) | Reviewed image build, SBOM, provenance and immutable release output              |

Release-specific status notes are evidence for their named release only. The production Compose file, current runbook and live post-deployment checks take precedence over an older status or validation note.

## Change and release model

CamCore changes use a reviewable, source-controlled workflow:

1. Fetch and verify current `main` before editing.
2. Make the smallest coherent change on an `agent/*` branch and preserve upstream compatibility.
3. Review the diff for secrets, private data, trust-boundary changes and accidental upstream drift.
4. Open a pull request and wait for the relevant repository validation to pass.
5. For branding or runtime changes, let the branding workflow build the reviewed source with its SBOM and provenance attestations.
6. Take the workflow's immutable image digest and pin it in a separate production Compose change. Never deploy `latest`, `camcore-current` or another mutable tag by itself.
7. Back up the persistent data, deploy through the approved Portainer process and complete the runbook's acceptance checks.
8. Record the exact source, image, deployment and live-verification state in the relevant operational change record.

GitHub Actions is the authoritative full validation environment. For documentation-only work, also run `git diff --check` and verify every relative link and operational claim against the current deployment files.

## Deployment verification

A release is not complete until the operator confirms, at minimum:

- the container is healthy and both `/health` and `/ready` succeed;
- the running image matches the approved immutable digest;
- no host port is published and only the approved networks are attached;
- Entra-only sign-in and both CamCore application roles behave correctly;
- a basic OpenAI chat completes without exposing or re-entering the provider key;
- CamCore Operations loads through verified TLS and remains read-only;
- disabled signup, sharing, upload, execution, retrieval and extension surfaces remain unavailable;
- configuration, CamCore identity and starter content return after a container recreation; and
- neither the AI workspace nor its tool gateway is exposed through public CamCore ingress.

Use the complete checklist in [`deploy/camcore/README.md`](deploy/camcore/README.md).

## Backup and rollback

`camcore-open-webui-data` contains the SQLite database and chat data. Take an encrypted cold backup before an upgrade, verify that it can be restored and retain the previous image with its matching pre-upgrade snapshot.

Never use `docker compose down --volumes` for an ordinary deployment. SQLite remains a single-worker, single-replica design until a reviewed migration introduces PostgreSQL, Redis and shared storage.

If acceptance fails, follow [`deploy/camcore/ROLLBACK.md`](deploy/camcore/ROLLBACK.md), restore the matching image and data state, then re-run the health, identity, access and core-chat checks.

## Upstream relationship

This repository is a maintained downstream of Open WebUI. CamCore changes should stay narrow and reviewable so upstream security fixes and improvements can be adopted without turning the fork into an unrelated rewrite.

Before an upstream upgrade:

1. review the new release notes and licence;
2. confirm that the CamCore branding remains permitted;
3. pin the exact upstream version, source revision and image digest;
4. re-review every fail-closed compatibility patch against that source;
5. rebuild and validate the CamCore image; and
6. promote the new digest only through a separate reviewed deployment change.

General Open WebUI documentation, feature requests and upstream product issues belong with the [upstream project](https://github.com/open-webui/open-webui). CamCore deployment, branding and operational matters belong with CamCore.

## Support and security reporting

For CamCore service help, use the [CamCore Support page](https://camcore.au/support) or email [help@camcore.au](mailto:help@camcore.au).

Do not place credentials, tokens, private topology, personal data or sensitive logs in a public issue. Report CamCore-specific security or deployment concerns through the approved private CamCore support path. Report vulnerabilities in the upstream Open WebUI product through [Open WebUI's private security reporting process](https://github.com/open-webui/open-webui/security).

## Licence and attribution

This repository contains code governed by multiple licences. See [`LICENSE_NOTICE`](LICENSE_NOTICE), [`LICENSE`](LICENSE) and [`LICENSE_HISTORY`](LICENSE_HISTORY) for the applicable terms and history.

The CamCore downstream retains Open WebUI copyright, attribution, repository provenance, bundled licence notices, SBOM and image ancestry. The CamCore identity layer may be deployed only while the deployment has no more than 50 end users in any rolling 30-day period, or while separate written or enterprise permission exists. See [`deploy/camcore/BRANDING.md`](deploy/camcore/BRANDING.md) before building, distributing or upgrading the branded image.

## Ownership

The CamCore deployment overlay is maintained as part of the private CamCore Network. Open WebUI remains the upstream project of Open WebUI Inc. and its contributors.
