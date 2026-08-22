# CamCore Open WebUI deployment

This overlay deploys one upstream-branded Open WebUI instance at
`https://ai.camcore.network` for internal CamCore access only. The service is not
published through the public `camcore.au` ingress and must remain reachable only
from the CamCore LAN or an approved private network path such as NetBird.

The production image is immutable:

```text
ghcr.io/open-webui/open-webui:v0.11.0@sha256:72c0ba641ba75e7aa52655cb242570906ececd09b1140fb736483038a22b3228
```

The service publishes no host port. Nginx Proxy Manager reaches port `8080` over
the external `npm-backend` network, while Open WebUI reaches only the
`camcore-ollama` alias on the external `camcore-ai-backend` network. The model
service must expose that alias on the shared private network and must not publish
port `11434`.

## Security posture

- Microsoft Entra is the only sign-in path. Password authentication, local signup,
  and account merging are disabled.
- Entra app roles are authoritative: `CamCore.AI.User` grants member access and
  `CamCore.AI.Admin` grants administrator access. Users with neither role remain
  pending and must not be admitted.
- The only enabled inference provider is private Ollama at
  `http://camcore-ollama:11434`.
- OpenAI-compatible passthrough, OAuth token exchange, ID-token cookies, profile
  image forwarding and user-info forwarding are disabled.
- Plugins, package installation, tool servers, terminal connections, API keys,
  code execution, web retrieval, uploads, image generation, memories, notes,
  automations, sub-agents, channels and user webhooks are disabled.
- The container drops all Linux capabilities, uses `no-new-privileges`, a PID
  limit, bounded temporary storage and rotated Docker logs.
- Audit output records metadata rather than prompt or response bodies.
- Runtime configuration is environment-authoritative. Admin-panel changes do not
  survive restart.
- Open WebUI naming, logos and required attribution remain upstream defaults.

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
   broad Microsoft Graph application permissions.
10. Keep the Entra client secret only in the Portainer stack environment or the
    approved secret-management process.

The browser performing OAuth must be able to resolve and reach
`ai.camcore.network` after Microsoft redirects it back to the application. This
works for CamCore LAN and correctly configured NetBird clients; it does not
require the application itself to be publicly reachable.

Open WebUI v0.11 promotes the first OAuth user to administrator as its bootstrap
behaviour, regardless of ordinary role mapping. The administrator-only first-login
sequence is therefore a security control.

## 2. Docker networks and secrets

Both external networks must exist before Portainer deploys the stack:

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

Populate all seven required variables from `.env.example` in the Portainer stack
environment. Generate the three Open WebUI secrets independently with at least 32
random bytes and keep them stable across ordinary redeployments.

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

## 4. Deploy and accept

Deploy `deploy/camcore/compose.yaml` as a single-replica Portainer stack. Do not
scale it while this release uses SQLite and one Uvicorn worker.

The change is accepted only after all of the following pass:

1. `camcore-open-webui` reports healthy and both `/health` and `/ready` succeed.
2. `docker port camcore-open-webui` prints no published host port.
3. `ai.camcore.network` resolves only through the intended CamCore private DNS path.
4. An unauthenticated browser reaching `https://ai.camcore.network` is redirected
   to Microsoft Entra with the exact registered callback.
5. The designated bootstrap operator was the first OAuth login and is an
   administrator; the backup administrator has also logged in successfully.
6. A user assigned only `CamCore.AI.User` can use the approved local model but
   cannot reach administrator settings or disabled features.
7. A tenant user with no app role is denied or remains pending.
8. A basic chat completes through private Ollama, and disconnecting Ollama fails
   closed rather than selecting an internet inference provider.
9. Local login/signup controls, uploads, sharing, API keys, tools, code execution,
   web search and external provider controls are absent or rejected.
10. Container logs contain no prompt bodies, responses, OAuth tokens or secret
    values.
11. The service is not reachable through the public `camcore.au` ingress.

## Backup, upgrade and rollback

`camcore-open-webui-data` contains the SQLite database, configuration state and
user chat data. Treat it as sensitive production data. Never use
`docker compose down --volumes` during an ordinary deployment.

For this single-replica SQLite release, take a cold encrypted backup:

1. Stop `camcore-open-webui` cleanly.
2. Snapshot or copy the complete `camcore-open-webui-data` volume while stopped.
3. Verify backup integrity, encryption, retention and a restore test.
4. Start the container and recheck health, Entra sign-in and one local-model chat.

Before an upgrade, verify the target upstream release and digest, review release
notes and licensing, take a verified cold backup, change the immutable image pin
through a pull request and repeat the acceptance checklist. Database migrations can
make an image-only rollback unsafe; restore both the previous image and its matching
pre-upgrade data snapshot when necessary.

SQLite remains supported only while this is a single-replica deployment. Design
and test PostgreSQL plus Redis and shared storage before adding workers or replicas.
