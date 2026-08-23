# CamCore Open WebUI deployment

This overlay deploys one **CamCore-branded Open WebUI** instance at
`https://ai.camcore.network` for internal CamCore access only. The service is not
published through the public `camcore.au` ingress and must remain reachable only
from the CamCore LAN or an approved private network path such as NetBird.

The production image is immutable and contains only the reviewed CamCore visual
overlay on top of the exact approved Open WebUI v0.11.0 runtime:

```text
ghcr.io/camcoreau/open-webui:camcore-0468f881f069c2cb67c0a279d8fdcd6830799bc5@sha256:bcaa07b4ba3306a13ed0a75c00839f17a2168c8e6bdfbe8ca489eb3ba0122f6c
```

The branding layer changes presentation only: CamCore colours, surfaces, browser
icon, loading treatment and `Jarvis | CamCore AI` identity. The application
runtime, authentication model, networks, persistent data and inference controls
remain the approved upstream-based deployment.

The service publishes no host port. Nginx Proxy Manager reaches port `8080` over
the external `npm-backend` network. Open WebUI also joins `camcore-ai-backend` so
it can continue reaching the temporary private Ollama migration backend without
publishing Ollama port `11434`. The container requires outbound HTTPS access to
`https://api.openai.com` for the primary OpenAI provider.

## Security posture

- Microsoft Entra is the only sign-in path. Password authentication, local signup,
  and account merging are disabled.
- Entra app roles are authoritative: `CamCore.AI.User` grants member access and
  `CamCore.AI.Admin` grants administrator access. Users with neither role remain
  pending and must not be admitted.
- OpenAI at `https://api.openai.com/v1` is the primary managed inference provider.
  The provider credential is supplied only through `CAMCORE_AI_OPENAI_API_KEY` in
  the production stack environment and must never be committed to Git.
- Private Ollama at `http://camcore-ollama:11434` remains enabled only during the
  OpenAI migration and rollback-validation period. Remove it after OpenAI has
  survived a full container recreation and normal production use is confirmed.
- `BYPASS_MODEL_ACCESS_CONTROL=true` is intentional for this approved provider
  set. Open WebUI v0.11 otherwise rejects raw provider models that have no local
  Workspace model row. Model admission is therefore controlled by Entra
  application assignment and the `CamCore.AI.User` / `CamCore.AI.Admin` roles.
- `BYPASS_ADMIN_ACCESS_CONTROL=false` remains enforced. Administrator privileges
  do not bypass the rest of Open WebUI's access-control checks.
- Direct provider connections, OAuth token exchange, ID-token cookies, profile
  image forwarding and user-info forwarding are disabled.
- Plugins, package installation, tool servers, terminal connections, user API
  keys, code execution, web retrieval, uploads, image generation, memories,
  notes, automations, sub-agents, channels and user webhooks remain disabled until
  a reviewed CamCore integration requires a specific capability.
- The container drops all Linux capabilities, uses `no-new-privileges`, a PID
  limit, bounded temporary storage and rotated Docker logs.
- Audit output records metadata rather than prompt or response bodies.
- Runtime configuration is environment-authoritative. Admin-panel changes do not
  survive restart; production settings must be represented in the compose file or
  stack environment.
- The CamCore banner and CamCore-specific starter prompts are therefore defined in
  the production compose so they are deterministic across redeployments.

Open WebUI administrators remain root-equivalent for this single-tenant instance.
Assign the administrator role only to trusted CamCore operators.

## 1. Microsoft Entra

Use the dedicated, single-tenant app registration named `CamCore AI`.

1. Configure a **Web** redirect URI exactly matching:

   ```text
   https://ai.camcore.network/oauth/microsoft/callback
   ```

2. Remove the old `https://ai.camcore.au/oauth/microsoft/callback` redirect URI
   once the internal hostname cutover is complete.
3. Keep the enabled application-role values exactly as:

   ```text
   CamCore.AI.User
   CamCore.AI.Admin
   ```

4. In the Enterprise Application, set **Assignment required** to **Yes**.
5. Before the first login, assign **only one designated bootstrap operator** to
   `CamCore.AI.Admin`. Do not assign ordinary members yet.
6. That designated operator **must be the first OAuth user** to reach the new
   Open WebUI data store. Verify the account is an administrator.
7. Assign a second emergency operator to `CamCore.AI.Admin` and complete one login
   with that account.
8. **Only after both administrator logins are verified** may approved members be
   assigned `CamCore.AI.User`.
9. Request only `openid`, `email`, `profile` and `offline_access`. Do not grant
   broad Microsoft Graph application permissions to the sign-in app.
10. Keep the Entra client secret only in the Dockge/Portainer stack environment or
    the approved secret-management process.

The browser performing OAuth must be able to resolve and reach
`ai.camcore.network` after Microsoft redirects it back to the application. This
works for CamCore LAN and correctly configured NetBird clients; it does not
require the application itself to be publicly reachable.

Open WebUI v0.11 promotes the first OAuth user to administrator as its bootstrap
behaviour, regardless of ordinary role mapping. The administrator-only first-login
sequence is therefore a security control.

## 2. Docker networks and secrets

Both external networks must exist before the stack is deployed:

```bash
docker network inspect npm-backend
docker network inspect camcore-ai-backend
```

Determine the exact NPM network subnet and set it as
`CAMCORE_AI_PROXY_TRUSTED_CIDR`:

```bash
docker network inspect npm-backend --format '{{(index .IPAM.Config 0).Subnet}}'
```

For the current Ganymede deployment this was verified as `172.21.0.0/16`; always
recheck after network recreation rather than assuming the value remains unchanged.
Never use `*`, `0.0.0.0/0` or the inference-network CIDR for proxy trust.

Populate all eight required variables from `.env.example` in the production
Dockge/Portainer stack environment:

```text
CAMCORE_AI_MICROSOFT_TENANT_ID
CAMCORE_AI_MICROSOFT_CLIENT_ID
CAMCORE_AI_MICROSOFT_CLIENT_SECRET
CAMCORE_AI_OPENAI_API_KEY
CAMCORE_AI_WEBUI_SECRET_KEY
CAMCORE_AI_OAUTH_SESSION_TOKEN_ENCRYPTION_KEY
CAMCORE_AI_OAUTH_CLIENT_INFO_ENCRYPTION_KEY
CAMCORE_AI_PROXY_TRUSTED_CIDR
```

The existing OpenAI project key may be used as the value of
`CAMCORE_AI_OPENAI_API_KEY`; do not place the value in this repository. The same
rule applies to the Microsoft client secret and the three stable Open WebUI secret
values. Generate the Open WebUI secrets independently with at least 32 random
bytes and keep them unchanged across ordinary redeployments.

With `ENABLE_PERSISTENT_CONFIG=false`, the OpenAI connection must come from these
environment-controlled values. This is deliberate: a container restart or image
replacement recreates the same approved provider configuration instead of relying
on a transient Admin-panel change.

## 3. Internal DNS and Nginx Proxy Manager

Create the internal DNS record:

```text
ai.camcore.network -> 192.168.5.29
```

Use the current Nginx Proxy Manager LAN address if it changes; do not create a
public DNS record for this service.

Create one Nginx Proxy Manager proxy host:

- Domain: `ai.camcore.network`
- Scheme: `http`
- Forward host: `open-webui`
- Forward port: `8080`
- WebSocket support: enabled
- Block common exploits: enabled
- TLS: enabled with a certificate trusted by CamCore client devices
- Force SSL: enabled
- HTTP/2: enabled
- HSTS: enabled when compatible with the chosen certificate and client policy

Recommended advanced configuration:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_buffering off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;
client_max_body_size 1m;
```

Do not add trusted-auth headers or a second authentication layer that bypasses the
native Microsoft Entra callback. Keep Open WebUI reachable only through Docker
networks and the internal reverse proxy.

## 4. OpenAI provider contract

Production enables one server-side OpenAI connection with:

```text
URL: https://api.openai.com/v1
Connection type: external
Authentication: bearer
Model filter: empty (provider model discovery)
Base model cache: disabled
```

The OpenAI key is never embedded in `compose.yaml`; the compose file references
`CAMCORE_AI_OPENAI_API_KEY` and fails closed when that variable is missing.

Open WebUI remains in offline mode for update/model-download behaviour. This does
not disable external LLM provider API calls or Microsoft OAuth. Automatic Hugging
Face model downloads remain blocked, so local RAG features must not be enabled
until their embedding-model requirements have been deliberately designed.

## 5. Deploy and accept

Deploy `deploy/camcore/compose.yaml` as a single-replica Dockge/Portainer stack.
Do not scale it while this release uses SQLite and one Uvicorn worker.

The change is accepted only after all of the following pass:

1. `camcore-open-webui` reports healthy and both `/health` and `/ready` succeed.
2. `docker port camcore-open-webui` prints no published host port.
3. `ai.camcore.network` resolves only through the intended CamCore private DNS path.
4. An unauthenticated browser reaching `https://ai.camcore.network` is redirected
   to Microsoft Entra with the exact registered callback.
5. The designated bootstrap operator was the first OAuth login and is an
   administrator; the backup administrator has also logged in successfully.
6. A user assigned only `CamCore.AI.User` can chat with approved provider models
   but cannot reach administrator settings or disabled features.
7. A tenant user with no app role is denied or remains pending.
8. OpenAI models are visible without re-entering the API key in Admin Settings and
   a basic chat completes successfully through `https://api.openai.com/v1`.
9. Restart or recreate `camcore-open-webui`, then verify the OpenAI connection,
   model list, CamCore banner and CamCore starter prompts all return automatically.
10. Private Ollama remains available only as the temporary migration fallback; it
    must not be exposed outside `camcore-ai-backend`.
11. Local login/signup controls, uploads, sharing, user API keys, arbitrary tool
    connections, code execution and web search are absent or rejected.
12. Container logs contain no prompt bodies, responses, OAuth tokens or secret
    values.
13. The service is not reachable through the public `camcore.au` ingress.
14. The loading screen, favicon, dark canvas, cyan/blue accents and raised surfaces
    visibly match the CamCore design language and the identity remains
    `Jarvis | CamCore AI`.

## 6. Ollama retirement gate

Do not remove the legacy Ollama data immediately. Retire the Ollama inference path
only after the OpenAI provider has passed the restart/recreation test above and has
been stable in normal use.

The retirement sequence is:

1. Confirm no CamCore workflow depends on the local Qwen/Ollama endpoint.
2. Set `ENABLE_OLLAMA_API=false` and remove `OLLAMA_BASE_URL` from the production
   compose through a reviewed change.
3. Redeploy and verify OpenAI chat, Entra sign-in and all health checks.
4. Stop/remove the old Jarvis/Ollama containers.
5. Retain the legacy Ollama volumes temporarily for rollback.
6. Delete the legacy volumes only after the rollback window has expired.

## Backup, upgrade and rollback

`camcore-open-webui-data` contains the SQLite database, configuration state and
user chat data. Treat it as sensitive production data. Never use
`docker compose down --volumes` during an ordinary deployment.

For this single-replica SQLite release, take a cold encrypted backup:

1. Stop `camcore-open-webui` cleanly.
2. Snapshot or copy the complete `camcore-open-webui-data` volume while stopped.
3. Verify backup integrity, encryption, retention and a restore test.
4. Start the container and recheck health, Entra sign-in and one OpenAI chat.

The CamCore branding image is a presentation-only layer over the approved upstream
runtime. A visual-only rollback may pin the previous known-good Open WebUI image,
but authentication, provider access and data compatibility must still be validated
before the rollback is promoted.

Before an upgrade, verify the target upstream release and digest, review release
notes and licensing, take a verified cold backup, rebuild the CamCore branding
layer on that exact upstream image, pin the resulting immutable image digest
through a pull request and repeat the acceptance checklist. Database migrations can
make an image-only rollback unsafe; restore both the previous image and its matching
pre-upgrade data snapshot when necessary.

SQLite remains supported only while this is a single-replica deployment. Design
and test PostgreSQL plus Redis and shared storage before adding workers or replicas.
