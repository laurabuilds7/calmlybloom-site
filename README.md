# calmlybloom-site

The marketing site for [calmlybloom.com](https://calmlybloom.com) — a calm, no-hype way into crypto for women curious about financial independence.

## How it works

- Single `index.html` at the root, no framework, no build step.
- Deployed via GitHub Pages from `main` branch root.
- Custom domain configured via `CNAME` file + DNS records at Porkbun.
- TLS handled by GitHub (Let's Encrypt, auto-renewed).

## Editing copy

Open `index.html`, edit the text between the tags, commit, push. Live in ~30 seconds.

### Placeholders to fill in

Search `index.html` for these tokens and replace with real values:

- `__CALENDLY_URL__` → e.g. `https://calendly.com/yourname/discovery-call`
- `__WHATSAPP_URL__` → e.g. `https://wa.me/27821234567` (international format, no `+`)

## Local preview

No build tools. Just open the file:

```
open index.html
```

Or run a tiny local server so relative links behave like production:

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Infrastructure

- **Registrar:** Porkbun
- **Host:** GitHub Pages (public repo, free tier)
- **DNS:** A records (apex → GitHub Pages IPs) + `www` CNAME → `laurabuilds7.github.io`
- **TLS:** "Enforce HTTPS" in repo Settings → Pages

## Research archive

`research/` contains the domain-research artifacts from the naming process:
`website-name-research.md`, the Python scripts, and cached API responses. Kept for provenance; not used by the site.
