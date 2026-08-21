# CamCore Open WebUI deployment

This overlay deploys one upstream-branded Open WebUI instance at
`https://ai.camcore.au`. It is intentionally separate from upstream application
source so the `camcoreau/open-webui` fork can remain easy to update.

The production image is immutable:

```text
ghcr.io/open-webui/open-webui:v0.11.0@sha256:72c0ba641ba75e7aa52655cb242570906ececd09b1140fb736483038a22b3228
```

The service publishes no host port. Nginx Proxy Manager reaches port `8080` over
the external `npm-backend` network, while Open WebUI reaches only the `camcore-ollama`
alias on the external `camcore-ai-backend` network. The model service must expose
that alias on the shared private network and must not publish port `11434`.

## Security posture

- Microsoft Entra is the only sign-in path. Password authentication, local signup,
  and account merging are disabled.
- Entra app roles are authoritative: `CamCore.AI.User` grants member access and
  `CamCore.AI.Admin` grants administrator access. Users with neither role remain
  pending and must not be admitted.
- The only enabled inference provider is private Ollama at
  `http://camcore-ollama:11434`. OpenAI-compatible passthrough, OAuth token
  exchange, ID-token cookies, profile-image URL forwarding, and identity forwarding
  are disabled.
- Plugins, package installation, tool servers, terminal connections, API keys,
  code execution, web retrieval, uploads, image generation, memories, notes,
  automations, sub-agents, channels, and user webhooks are disabled.
- The container has all Linux capabilities dropped, `no-new-privileges`, a PID
  limit, a bounded temporary filesystem, and rotated Docker logs. Audit output
  records metadata, not prompt or response bodies. The official v0.11.0 image
  rewrites bundled static assets at startup, so its container layer cannot be
  forced read-only without a separately maintained derived image; that layer is
  disposable and only `/app/backend/data` is persisted.
- Runtime configuration is environment-authoritative. Admin-panel changes do not
  survive restart.
- Open WebUI naming, logos, and required attribution remain upstream defaults. Do
  not remove or obscure upstream branding without confirming that the intended
  use complies with the current [Open WebUI license](https://docs.openwebui.com/license/).

Open WebUI administrators remain root-equivalent for this single-tenant instance.
Assign the admin role only to trusted CamCore operators.

## 1. Prepare Microsoft Entra

Create a dedicated, tenant-only app registration named `CamCore AI`. Do not reuse
a browser SPA registration or another CamCore service identity.

1. Add a **Web** redirect URI exactly matching
   `https://ai.camcore.au/oauth/microsoft/callback`.
2. Create enabled application roles whose values are exactly
   `CamCore.AI.User` and `CamCore.AI.Admin`.
3. In the Enterprise Application, set **Assignment required** to **Yes**.
4. Before the first login, assign **only one designated bootstrap operator** to
   `CamCore.AI.Admin`. Do not assign `CamCore.AI.User` to any member yet.
5. After deployment, that designated operator must be the first OAuth user. Verify
   the resulting account is an administrator, then assign a second emergency
   operator to `CamCore.AI.Admin` and have that operator complete one login.
6. Only after both administrator logins are verified may approved members be
   assigned to `CamCore.AI.User`.
7. Use only the OpenID scopes requested by the compose file (`openid`, `email`,
   `profile`, and `offline_access`). Do not grant broad Microsoft Graph application
   permissions.
8. Create a time-limited client secret, record its expiry in the CamCore secret
   rotation process, and store the value only in the deployment secret manager.

Open WebUI v0.11 promotes the first OAuth user to administrator as its bootstrap
behaviour, regardless of the ordinary role mapping. The admin-only assignment and
first-login sequence above is therefore a security control, not an optional
convenience. If any other identity reaches the instance first, stop the rollout
and remediate the fresh instance before assigning members or retaining user data.

Creating or rotating the Entra client secret changes persistent access. Carry it
out in an approved change window and never paste the value into source control,
CI logs, chat, screenshots, or shell history.

## 2. Prepare networks and secrets

Both external networks must exist on the Docker host before Portainer deploys the
stack:

```bash
docker network inspect npm-backend
docker network inspect camcore-ai-backend
```

Determine the exact proxy-network subnet and set it as
`CAMCORE_AI_PROXY_TRUSTED_CIDR`:

```bash
docker network inspect npm-backend --format '{{(index .IPAM.Config 0).Subnet}}'
```

Never use `*`, `0.0.0.0/0`, or the inference-network CIDR for proxy trust. Populate
all seven required variables from `.env.example` in the Portainer stack environment.
Generate the three application secrets independently with at least 32 random bytes
and keep them stable for the lifetime of the data volume. Rotating them invalidates
sessions and can make encrypted OAuth material unreadable.

Before deployment, render the effective configuration without printing it into a
shared log:

```bash
docker compose --env-file /secure/path/camcore-open-webui.env \
  -f deploy/camcore/compose.yaml config --quiet
```

## 3. Configure DNS and Nginx Proxy Manager

Create or verify the `ai.camcore.au` DNS record against the current CamCore ingress
address at change time. Do not copy a remembered address without rechecking it.

Create one Nginx Proxy Manager host:

- Domain: `ai.camcore.au`
- Scheme: `http`
- Forward host: `open-webui`
- Forward port: `8080`
- WebSocket support: enabled
- Block common exploits: enabled
- Certificate: valid public certificate, Force SSL, HTTP/2, and HSTS enabled

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
native Entra callback. Keep the upstream container reachable only on Docker
networks.

## 4. Deploy and accept

Deploy `deploy/camcore/compose.yaml` as a single-replica Portainer stack. Do not
scale it: this first release deliberately uses Open WebUI's SQLite data store and
one Uvicorn worker.

The change is accepted only after all of the following pass:

1. `camcore-open-webui` reports healthy; both `/health` and `/ready` return success.
2. `docker port camcore-open-webui` prints no published port.
3. `https://ai.camcore.au` redirects an unauthenticated browser to the dedicated
   Microsoft sign-in flow with the exact registered callback.
4. The designated bootstrap operator was the first OAuth login and is an
   administrator; a separately assigned backup administrator has also logged in.
5. Member assignments were created only after those two administrator checks.
6. A user assigned only `CamCore.AI.User` can chat with the approved local model
   but cannot reach admin settings or any disabled feature.
7. An otherwise valid tenant user with no app role is denied/pending.
8. A basic chat completes through private Ollama, and stopping or disconnecting
   that backend fails closed rather than selecting an internet provider.
9. Local login/signup controls, uploads, sharing, API keys, tools, code execution,
   web search, and external provider controls are absent or rejected.
10. Desktop and mobile views have no overflow or authentication-loop defects.
11. Container logs show metadata-only audit entries and contain no prompt bodies,
    responses, OAuth tokens, or secret values.

## Backup, upgrade, and rollback

`camcore-open-webui-data` contains the SQLite database, configuration state, and
user chat data. Treat it as sensitive production data. Never run
`docker compose down --volumes` and never delete or recreate the named volume as
part of an ordinary deployment.

Do not commit changes made inside the running container or treat its writable
container layer as storage. Recreating the service must discard that layer; only
the named data volume is backed up and restored.

For this single-replica SQLite release, take a **cold, encrypted** volume backup:

1. Announce the maintenance window and stop `camcore-open-webui` cleanly.
2. Copy or snapshot the complete `camcore-open-webui-data` volume with the approved
   host backup system while the container remains stopped.
3. Verify the backup manifest, encryption, retention, and a restore test.
4. Start the container and recheck `/health`, `/ready`, Entra login, and one chat.

Before an upgrade, verify the target release and digest from upstream, review its
release notes and license, take a verified cold backup, change the immutable image
pin through a pull request, and repeat the full acceptance checklist. Database
migrations can make an image-only rollback unsafe; rollback means restoring both
the previous image digest and its matching pre-upgrade data snapshot.

SQLite is acceptable only while this remains a single replica. Before adding
workers or replicas, design and test PostgreSQL plus Redis, shared file storage,
coordinated database migrations, and a restore procedure. Do not point multiple
Open WebUI processes at this SQLite volume.

Useful upstream references:

- [Open WebUI v0.11.0 release](https://github.com/open-webui/open-webui/releases/tag/v0.11.0)
- [Environment variable reference](https://docs.openwebui.com/reference/env-configuration/)
- [Authentication and SSO](https://docs.openwebui.com/features/authentication-access/auth/sso/)
- [Production hardening](https://docs.openwebui.com/getting-started/advanced-topics/hardening/)
