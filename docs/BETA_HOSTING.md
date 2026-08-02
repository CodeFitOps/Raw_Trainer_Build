# RawTrainer — Beta hosting runbook

How to put the web GUI in front of external beta testers, starting from the DEV
Mac and moving to the cloud later. Written for the current codebase: a FastAPI
app (`src/ui/web/api.py`) serving a JSON API plus the PWA at `static/index.html`.

---

## Read this first: what the app does and does *not* do yet

- **No authentication.** Every endpoint is open, including the ones that *write*:
  `POST /api/import`, `DELETE /api/workouts/{id}`, `POST /api/runs`. Anyone who
  can reach the app can add or delete workouts. **A gate in front is mandatory
  before exposing it** — never port-forward this straight to the internet.
- **Single-tenant data.** There is one `data/workouts_files/` library and one
  `.run_logs_v2/` history, shared by everyone who connects. For a small trusted
  beta that's fine (see "shared vs per-user" at the end), but be explicit with
  testers that they're sharing one library and one stats pile.
- **It's offline-first only when the server is local.** Once the server is
  remote, phones need a connection. The driven timer already fetches the whole
  timeline up front and runs client-side, so a brief signal drop mid-session is
  survivable; only the end-of-session save needs the network.

---

## Phase 1 — expose the DEV Mac with a Cloudflare Tunnel

You already run `rawtrainer.eu` on Cloudflare, so this costs nothing extra and
gives you `beta.rawtrainer.eu` with real HTTPS, **no router port-forwarding, and
your home IP stays hidden** (the tunnel makes an outbound connection).

### 1. Run the app bound to localhost only

Bind to `127.0.0.1`, *not* `0.0.0.0`, so the only way in is through the tunnel:

```bash
cd /Users/mpino/repos/CodeFitOps/rawtrainer/RawTrainer_build
python -m venv .venv && source .venv/bin/activate   # if not already
pip install -r requirements.txt
uvicorn src.ui.web.api:app --host 127.0.0.1 --port 8000
```

Keep one worker for the beta — the file-based storage can race with several.

To stop the Mac sleeping while it serves, wrap it in `caffeinate`:

```bash
caffeinate -s uvicorn src.ui.web.api:app --host 127.0.0.1 --port 8000
```

### 2. Install cloudflared

```bash
brew install cloudflared
```

### 3a. Quick throwaway URL (fastest, for a first smoke test)

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Prints a `https://<random>.trycloudflare.com` URL that proxies to your app.
Good for a 5-minute test; the URL changes every run and has no auth, so don't
share it widely.

### 3b. Stable named tunnel on beta.rawtrainer.eu (recommended)

```bash
cloudflared tunnel login                      # authorize the rawtrainer.eu zone
cloudflared tunnel create rawtrainer-beta     # creates a tunnel + credentials json (a UUID)
cloudflared tunnel route dns rawtrainer-beta beta.rawtrainer.eu
```

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <UUID-from-create>
credentials-file: /Users/mpino/.cloudflared/<UUID-from-create>.json
ingress:
  - hostname: beta.rawtrainer.eu
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Run it:

```bash
cloudflared tunnel run rawtrainer-beta
```

To keep it running in the background as a login service:

```bash
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared   # or: brew services start cloudflared
```

---

## Phase 1 login — Cloudflare Access (this is your beta "log in")

Access sits in front of the tunnel and authenticates people *before* they reach
the app, so you get a real login without writing a line of auth code.

1. Cloudflare dashboard → **Zero Trust → Access → Applications → Add an
   application → Self-hosted**.
2. **Application domain:** `beta.rawtrainer.eu`.
3. Add a **policy**: Action *Allow*, and an include rule — either
   *Emails* (list your testers' addresses) or *Emails ending in* a domain you
   trust. Leave the default **One-time PIN** login method on.
4. Save. Now visiting `beta.rawtrainer.eu` prompts for an email, emails a
   one-time code, and only lets listed testers through.

Optional niceties: add **Google** (or GitHub) as an identity provider for
one-click sign-in instead of PIN emails, and set a session duration so testers
aren't re-prompted daily.

That is enough to run the beta: gated access, real HTTPS, stable URL, your Mac
at home, and zero app changes.

---

## When testers need their *own* data — the per-user step

Access can hand identity to the app: every authenticated request carries a
`Cf-Access-Authenticated-User-Email` header (and a signed JWT). The app can
trust that as the user key and namespace storage per user, e.g.
`data/users/<email>/workouts_files/` and a per-user run-log dir. That's a change
in `src/application/library.py` and `src/infrastructure/run_log.py` (a per-user
data root threaded through), **not** a new auth system — no passwords to store.
Do this only once testers actually ask for private libraries; the shared gate is
the right default to start.

Keep the local, no-login path (`uvicorn` on your own machine, direct) intact for
your own use — the gate is a deployment wrapper, not a change to what RawTrainer
is.

---

## Phase 2 — move to a cloud provider

The app is one Python process plus files, so it containerizes trivially. The one
thing to get right: **the data is on disk, so you need a persistent volume** — a
plain container filesystem is wiped on redeploy and you'd lose run logs.

Minimal `Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
CMD ["uvicorn", "src.ui.web.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

Provider options, cheapest path first:

- **Fly.io / Render** — give you TLS and a URL out of the box; attach a volume
  (Fly volume / Render disk) mounted where `data/` and `.run_logs_v2/` live.
- **Small VPS (Hetzner, etc.)** — run the container behind Caddy or nginx for
  TLS, or keep the exact same Cloudflare Tunnel setup pointing at the VPS
  instead of the Mac. Reusing the tunnel means the Access gate keeps working
  unchanged.

Carry the same two rules across: keep it to **one worker** until per-user data
lands, and **back up** the `data/` and run-log directories (they're your users'
history).

---

## Quick reference

| Need | Do |
|------|----|
| First 5-min test | `cloudflared tunnel --url http://127.0.0.1:8000` |
| Stable beta URL | named tunnel → `beta.rawtrainer.eu` |
| Login for testers | Cloudflare Access policy (email allowlist / OTP) |
| Don't let the Mac sleep | `caffeinate -s uvicorn ...` |
| Keep API safe | bind `127.0.0.1`, gate with Access, 1 worker |
| Per-user data (later) | trust `Cf-Access-Authenticated-User-Email`, namespace data dirs |
