# calmlybloom-site — agent guide

Guidance for Claude Code (and other agents) working in this repo. Humans should read `README.md` instead.

## Repo shape

- Static one-page site. Single `index.html` at the root, embedded CSS, no build step, no framework.
- Hosted on GitHub Pages from `main` branch root.
- Custom domain pinned by the `CNAME` file (`calmlybloom.com`).
- TLS handled by GitHub (Let's Encrypt, auto-renewed).
- `research/` contains naming-research artifacts. Not used by the live site — kept for provenance.

## Current state

The site is currently a minimal holding page pending content review by the owner. Do not expand the holding page, restore the prior draft, or re-enable GitHub Pages without explicit owner confirmation. The full prior draft is preserved at `index.full-draft.html` (gitignored on disk) and at git commit `90dad6c` — leave those alone unless the owner asks.

DNS at the registrar is already wired to GitHub Pages, so re-enabling Pages would resume serving the custom domain immediately. Treat that as a deploy gate, not a routine action.

## Editing flow

1. Edit `index.html` in place.
2. Commit with a Conventional Commits prefix (`feat:`, `fix:`, `content:`, `infra:`, `docs:`, `chore:`).
3. Push to `main`. If Pages is enabled, the change is live in ~30 seconds.

Local preview: `python3 -m http.server 8000` then open `http://localhost:8000`. No build tools required.

## Porkbun API

DNS and domain admin go through Porkbun. The owner's domains have per-domain API access enabled; if a future domain doesn't, toggle it at Domain Management → `<domain>` → Details → API Access.

### Credentials

Live in `~/Projects/better-out-co/.env` (shared across the owner's repos):

```
PORKBUN_API_KEY=...
PORKBUN_SECRET_KEY=...
```

Load with:

```bash
set -a; source ~/Projects/better-out-co/.env; set +a
```

Never commit the `.env` or echo the key values into shell history / logs.

### Auth shape

All endpoints are `POST` to `https://api.porkbun.com/api/json/v3<path>` with a JSON body that includes the credentials inline (no `Authorization` header):

```json
{
  "apikey": "pk1_...",
  "secretapikey": "sk1_...",
  "...endpoint-specific fields..."
}
```

Minimal Python pattern:

```python
import json, urllib.request, os
KEY = os.environ["PORKBUN_API_KEY"]
SEC = os.environ["PORKBUN_SECRET_KEY"]

def call(path, body=None):
    payload = {"apikey": KEY, "secretapikey": SEC}
    if body:
        payload.update(body)
    req = urllib.request.Request(
        f"https://api.porkbun.com/api/json/v3{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())
```

### Gotchas (learned the hard way)

- **`checkDomain` rate limit is 1 request per 10 seconds**, not 1/sec. Exceeding it returns HTTP 503 with no clear message. For bulk availability checks, sleep ≥10s between calls and cache aggressively. See `research/research.py` and `research/porkbun-cache.json` for the working pattern.
- **Per-domain API access must be toggled on** before any DNS or domain-edit endpoint will work for that specific domain. Account-level API access is necessary but not sufficient.
- **Response data is nested under a `response` sub-key** for some endpoints (e.g. `pricing/get`), not at the top level. Always inspect the shape before parsing.
- For bulk pricing without per-domain checks, `pricing/get` returns the public registry-list pricing for every TLD in one call and is not rate-limited the same way. Use it for baseline pricing, then fall back to `checkDomain` only for the shortlist.

### Useful endpoints

- `POST /ping` — sanity-check credentials.
- `POST /domain/listAll` — list domains on the account.
- `POST /dns/retrieve/<domain>` — read DNS records.
- `POST /dns/create/<domain>` — add a DNS record.
- `POST /dns/edit/<domain>/<id>` — edit a record.
- `POST /dns/delete/<domain>/<id>` — delete a record.
- `POST /domain/checkDomain/<domain>` — availability + price (rate-limited).
- `POST /pricing/get` — list pricing for all TLDs (no rate limit issues).

Full docs: <https://porkbun.com/api/json/v3/documentation>

## DNS for this domain

`calmlybloom.com` is configured for GitHub Pages:

- Apex `A` records: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
- `www` `CNAME`: `laurabuilds7.github.io`

If you ever need to recreate this from scratch, those four A records at the apex plus the `www` CNAME are the canonical GitHub Pages setup.

## What NOT to do without owner confirmation

- Re-enable GitHub Pages on this repo.
- Restore `index.full-draft.html` to `index.html`.
- Change the `CNAME` file or DNS records at the registrar.
- Make the repo private (Pages with a custom domain requires a paid plan when private — flag the cost first).
- Push commits that revert the holding-page state.
- Add forms, lead capture, analytics, or third-party scripts to the holding page.
