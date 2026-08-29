# CamCore Open WebUI deployment

This overlay deploys one **CamCore-branded Open WebUI** instance at
`https://ai.camcore.network` for internal CamCore access only. The service is not
published through the public `camcore.au` ingress and must remain reachable only
from the CamCore LAN or an approved private network path such as NetBird.

The production image is immutable and contains the reviewed CamCore visual overlay
on top of the exact approved Open WebUI v0.11.0 runtime:

```text
ghcr.io/camcoreau/open-webui:camcore-4d85a50720f227d69c85dc6256fdbdc970ce138a@sha256:cfc5c4e4d63e8779d86d1cc56807555dc42b0d65217af0c6efbd209eaf30ff7d
```

The service publishes no host port. Nginx Proxy Manager reaches Open WebUI over
`npm-backend`. Open WebUI no longer joins the legacy `camcore-ai-backend` network
or depends on Ollama/OpenJarvis. CamCore Operations traffic goes to
`https://ai-tools.camcore.network` with TLS verification enabled, then NPM forwards
to the standalone gateway over a dedicated two-service network.

## Security posture

- Microsoft Entra is the only sign-in path. Password authentication, local signup
  and account merging are disabled.
- Entra app roles are authoritative: `CamCore.AI.User` grants member access and
  `CamCore.AI.Admin` grants administrator access.
- OpenAI at `https://api.openai.com/v1` is the production inference provider. Its
  key is supplied only through `CAMCORE_AI_OPENAI_API_KEY` in Portainer.
- Local Ollama inference is disabled; Open WebUI has no runtime dependency on the
  legacy OpenJarvis stack.
- The only globally configured external tool server is the private CamCore
  Operations Gateway at `https://ai-tools.camcore.network`. It exposes a reviewed
  read-only OpenAPI surface and requires `CAMCORE_AI_GATEWAY_API_KEY`.
- The gateway is a standalone CamCore service from
  `camcoreau/camcore-ai-gateway`; OpenJarvis is not part of the gateway runtime.
- Open WebUI explicitly keeps tool-server TLS certificate verification enabled.
- `BYPASS_MODEL_ACCESS_CONTROL=true` is intentional for the approved provider set;
  Entra application assignment and CamCore app roles remain the admission boundary.
- `BYPASS_ADMIN_ACCESS_CONTROL=false` remains enforced.
- User-created direct tool servers, plugins, package installation, terminal
  servers, user API keys, code execution, web retrieval, uploads, image generation,
  memories, notes, automations, sub-agents, channels and user webhooks remain off.
- The container drops all Linux capabilities, uses `no-new-privileges`, a PID
  limit, bounded temporary storage and rotated Docker logs.
- Audit output records metadata rather than prompt or response bodies.
- Runtime configuration is environment-authoritative. Admin-panel changes do not
  survive restart; production settings belong in Git or the Portainer environment.

## 1. Microsoft Entra

Use the dedicated, single-tenant app registration named `CamCore AI`.

1. Configure the Web redirect URI exactly as:

   ```text
   https://ai.camcore.network/oauth/microsoft/callback
   ```

2. Keep the application-role values exactly as `CamCore.AI.User` and
   `CamCore.AI.Admin`, with Enterprise Application **Assignment required = Yes**.
3. Before first login, assign **only one designated bootstrap operator** to
   `CamCore.AI.Admin`.
4. That designated operator **must be the first OAuth user** to reach a new Open
   WebUI data store. Verify the account is an administrator.
5. Assign a second emergency operator to `CamCore.AI.Admin` and complete one login.
6. **Only after both administrator logins are verified** may approved members be
   assigned `CamCore.AI.User`.
7. Request only `openid`, `email`, `profile` and `offline_access` for the sign-in
   application.
8. Keep the Entra client secret only in Portainer or the approved secret store.

## 2. Required Open WebUI network and secrets

The Open WebUI production network must exist before deployment:

```text
npm-backend
```

Determine the exact `npm-backend` subnet and set it as
`CAMCORE_AI_PROXY_TRUSTED_CIDR`. Never use `*` or `0.0.0.0/0`.

Populate these required Portainer environment variables:

```text
CAMCORE_AI_MICROSOFT_TENANT_ID
CAMCORE_AI_MICROSOFT_CLIENT_ID
CAMCORE_AI_MICROSOFT_CLIENT_SECRET
CAMCORE_AI_OPENAI_API_KEY
CAMCORE_AI_GATEWAY_API_KEY
CAMCORE_AI_WEBUI_SECRET_KEY
CAMCORE_AI_OAUTH_SESSION_TOKEN_ENCRYPTION_KEY
CAMCORE_AI_OAUTH_CLIENT_INFO_ENCRYPTION_KEY
CAMCORE_AI_PROXY_TRUSTED_CIDR
```

`CAMCORE_AI_GATEWAY_API_KEY` must be a separate high-entropy service credential;
do not reuse the OpenAI project key, Entra secret or WebUI encryption keys. Store
the same gateway value in both the `camcore-ai-gateway` and `camcore-open-webui`
Portainer stack environments. Never commit the populated value to Git.

With `ENABLE_PERSISTENT_CONFIG=false`, the approved OpenAI and CamCore Operations
connections are recreated from environment-controlled values after every container
recreation.

## 3. Internal DNS and Nginx Proxy Manager

Open WebUI keeps its existing private route:

```text
ai.camcore.network -> current internal Nginx Proxy Manager address
```

Proxy `ai.camcore.network` to `open-webui:8080` over `npm-backend` with TLS, Force
SSL and WebSocket support enabled.

### CamCore Operations Gateway

Create a separate external Docker network on Ganymede:

```text
camcore-ai-operations
```

Persistently attach **only** these services to that network:

```text
nginx-proxy-manager
camcore-ai-gateway
```

Do not attach Open WebUI, Ollama, the legacy OpenJarvis service or unrelated
containers to `camcore-ai-operations`.

Create private DNS:

```text
ai-tools.camcore.network -> current internal Nginx Proxy Manager address
```

Do not create a public DNS record or public ingress for this hostname.

Create an NPM proxy host:

```text
Domain: ai-tools.camcore.network
Scheme: http
Forward host: camcore-ai-gateway
Forward port: 8100
TLS: enabled with a certificate trusted by the Open WebUI container
Force SSL: enabled
HTTP/2: enabled
Public exposure: none
```

NPM terminates validated TLS. The only unencrypted hop is NPM to the gateway across
the dedicated two-member `camcore-ai-operations` network. Open WebUI must not have
tool-server certificate verification disabled as a shortcut.

## 4. OpenAI provider contract

Production enables one server-side OpenAI connection:

```text
URL: https://api.openai.com/v1
Connection type: external
API mode: Chat Completions (`/v1/chat/completions`)
Authentication: bearer
Model filter: provider discovery
Base model cache: disabled
Ollama: disabled
```

The OpenAI key is never embedded in `compose.yaml`; the stack fails closed if
`CAMCORE_AI_OPENAI_API_KEY` is absent.

Responses mode is temporarily disabled after live acceptance found that Open
WebUI v0.11.0 opened the upstream Responses stream but did not deliver any text
or completion event to the signed-in chat UI. Do not re-enable
`api_type=responses` until both ordinary streaming and the full reasoning-plus-tool
continuation have passed live validation. While this rollback is active, GPT-5.6
reasoning above `none` cannot be combined with function tools through Chat
Completions.

## 5. CamCore Operations tool contract

Production defines one global OpenAPI tool-server connection:

```text
Name: CamCore Operations
URL: https://ai-tools.camcore.network
Schema: openapi.json
Authentication: Bearer CAMCORE_AI_GATEWAY_API_KEY
TLS verification: enabled
```

The gateway is deployed independently from `camcoreau/camcore-ai-gateway`,
publishes no host port and is reachable by NPM only through
`camcore-ai-operations`. Provider credentials and upstream service URLs remain
server-side in the gateway Portainer stack; model arguments cannot replace them.

The initial tool surface is deliberately **read-only** and includes bounded health,
logs, infrastructure, documentation and service-status operations. It does not
expose container restart, deployment, DNS changes, Proxmox actions, NetBird policy
changes, media deletion or other modifying operations. Those require a separate
Open WebUI-native confirmation layer before production enablement.

## 6. Deploy and accept

Deploy the standalone gateway first from
`camcoreau/camcore-ai-gateway/deploy/camcore/compose.yaml`. Set
`CAMCORE_AI_GATEWAY_RELEASE` to the published gateway commit SHA and provide the
same `CAMCORE_AI_GATEWAY_API_KEY` value that will be used by Open WebUI. Then deploy
this repository's `deploy/camcore/compose.yaml` as the single-replica Open WebUI
**Portainer** stack.

The change is accepted only after all of the following pass:

1. `camcore-ai-gateway` reports healthy on its private operations network.
2. `camcore-open-webui` reports healthy and `/health` plus `/ready` succeed.
3. Neither service publishes a host port.
4. Entra-only sign-in and the CamCore application roles behave as expected.
5. OpenAI models are visible and a basic chat completes without re-entering the key.
6. No Ollama models/provider entry are exposed by Open WebUI.
7. `https://ai-tools.camcore.network/health` is reachable from the Open WebUI
   container and certificate validation succeeds.
8. `CamCore Operations` appears as the GitOps-controlled tool server and its schema
   loads from `https://ai-tools.camcore.network/openapi.json`.
9. Asking Jarvis to **Check CamCore health** with a Chat Completions-compatible
   model configuration can invoke `get_camcore_health`; missing or failed
   integrations are reported as unavailable rather than healthy.
10. Restart/recreate Open WebUI and confirm the OpenAI connection, CamCore
    Operations connection, banner and starter prompts all return automatically;
    repeat the basic chat check.
11. Local login/signup, uploads, public sharing, user API keys, arbitrary tool
    connections, modifying tools, code execution and web search remain unavailable.
12. Neither `ai.camcore.network` nor `ai-tools.camcore.network` is reachable through
    public CamCore ingress.

## 7. Legacy OpenJarvis/Ollama retirement

This Open WebUI configuration no longer requires OpenJarvis, Ollama or the
`camcore-ai-backend` network. After the acceptance checks above pass:

1. Stop/remove the legacy `camcore-jarvis` and `camcore-jarvis-ollama` runtime
   containers while keeping `camcore-ai-gateway` running independently.
2. Confirm `Jarvis | CamCore AI` still provides OpenAI chat and CamCore Operations.
3. Retain legacy Ollama volumes only for the agreed rollback window, then remove
   them after a final backup/rollback decision.
4. Remove the unused `camcore-ai-backend` Docker network when no remaining service
   references it.
5. Archive or retire the legacy `camcoreau/jarvis` deployment after no production
   stack references it.

## Backup and upgrade

`camcore-open-webui-data` contains SQLite state and chat data. Never use
`docker compose down --volumes` for an ordinary deployment. Take an encrypted cold
backup before upgrades, verify restore integrity, and keep the prior image plus its
matching pre-upgrade data snapshot available for rollback.

SQLite remains a single-replica design. Move to PostgreSQL/Redis and shared storage
before adding workers or replicas.
