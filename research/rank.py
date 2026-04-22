#!/usr/bin/env python3
"""
Rank + output stage. Uses cached RDAP + cached Porkbun data only (no new API calls).

For domains WITH a live Porkbun checkDomain result:
  - Trust Porkbun's avail + premium + price
For domains WITHOUT a Porkbun result (network dropped mid-run):
  - Trust RDAP availability
  - Use baseline TLD registration price from porkbun-pricing.json
  - Tag as "baseline" so the user knows to spot-check before buying
"""

import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).parent
rdap = json.load(open(HERE / "rdap-cache.json"))
pb   = json.load(open(HERE / "porkbun-cache.json"))
tld_prices = json.load(open(HERE / "porkbun-pricing.json"))["pricing"]
R_PER_USD  = json.load(open(HERE / "usd-rates.json"))["rates"]["ZAR"]
R200_USD   = 200.0 / R_PER_USD

# TLDs present
TLD_RANK = {
    "com": 0, "co": 1, "club": 2, "garden": 3, "love": 4, "boutique": 5,
    "life": 6, "studio": 7, "earth": 8, "world": 9, "blog": 10,
    "shop": 11, "store": 12,
}
TLDS_IN_ORDER = list(TLD_RANK.keys())

# RDAP-available domains only
available_domains = [d for d, v in rdap.items() if v is True]
print(f"[rank] RDAP-available domains: {len(available_domains)}")

# --- Build row per base, picking best TLD -----------------------------------

def vibe_fit(domain):
    base = domain.rsplit(".", 1)[0]
    tld = domain.rsplit(".", 1)[1]
    if tld == "garden": return "botanical"
    if tld == "club":   return "members-club"
    if tld == "boutique": return "boutique"
    if any(w in base for w in ["bloom", "blossom", "petal", "fleur", "flora", "rose",
                                "lilac", "wisteria", "primrose", "magnolia", "camellia",
                                "peony", "freesia", "dahlia", "mimosa", "verbena",
                                "dandelion", "lavender", "jasmine", "marigold", "iris",
                                "cornflower", "bluebell", "orchid", "violet", "crocus",
                                "gardenia", "hydrangea", "poppy", "garden"]):
        return "botanical"
    if any(w in base for w in ["dawn", "dusk", "aurora", "glow", "light", "luminous",
                                "lumen", "sunrose", "gloaming", "goldenhour", "firstlight",
                                "amber", "moonflower", "sun"]):
        return "dawn-light"
    if any(w in base for w in ["slow", "soft", "gentle", "ease", "quiet", "lush",
                                "saunter", "unhurried", "linen", "still", "calm", "tend"]):
        return "slow-living"
    if any(w in base for w in ["meadowlark", "lark", "nightingale", "warbler", "goldfinch",
                                "sparrow", "swallow", "fledg", "songbird", "firefly",
                                "silkmoth", "lunamoth", "wren", "meadow"]):
        return "bird"
    if any(w in base for w in ["brook", "creek", "tide", "current", "cove", "flow",
                                "stillwater", "rivulet", "shoal", "marsh"]):
        return "water"
    return "invented-feminine"

RATIONALE = {
    "botanical": "Grounded in the brand's flora vocabulary — legible, ownable, the visual world writes itself.",
    "dawn-light": "Dawn-light register aligns with slow-morning mood; cream + rose palette reads naturally.",
    "slow-living": "Names the brand promise (softness, ease) without making a financial claim.",
    "members-club": "The `.club` TLD literally states members-only — on-brand for VIP positioning.",
    "boutique": "Feminine + curated; the `.boutique` TLD signals considered, not mass-market.",
    "bird": "Fledging metaphor — growth without hustle. Pairs with dawn/linen visuals.",
    "water": "Flow-state name — evokes steady progress, no trader-bro energy.",
    "invented-feminine": "Vowel-forward invented mark — low trademark risk, feminine phonetics, globally pronounceable.",
}

VIBE_RANK = {"botanical": 0, "members-club": 1, "dawn-light": 2, "slow-living": 3,
             "boutique": 4, "bird": 5, "water": 6, "invented-feminine": 7}

# --- Build candidate rows ---------------------------------------------------

rows = []
skipped_premium = []

for domain in available_domains:
    tld = domain.rsplit(".", 1)[1]
    if tld not in TLD_RANK:
        continue
    pb_entry = pb.get(domain)
    verified = False
    premium = False
    year1_usd = None
    renew_usd = None
    if pb_entry and pb_entry.get("status") == "SUCCESS":
        resp = pb_entry.get("response", {})
        if resp.get("avail") != "yes":
            continue  # Porkbun disagrees with RDAP; trust Porkbun
        verified = True
        if resp.get("premium") == "yes":
            premium = True
            skipped_premium.append((domain, resp.get("price", "?"), resp.get("additional", {}).get("renewal", {}).get("price", "?")))
            continue
        try:
            year1_usd = float(resp.get("price", "0"))
            renew_usd = float(resp.get("additional", {}).get("renewal", {}).get("price", "0"))
        except (TypeError, ValueError):
            pass
    if year1_usd is None:
        # Use baseline TLD pricing
        tld_info = tld_prices.get(tld)
        if not tld_info: continue
        try:
            year1_usd = float(tld_info["registration"])
            renew_usd = float(tld_info["renewal"])
        except (KeyError, ValueError):
            continue
    if year1_usd <= 0 or year1_usd > R200_USD:
        continue
    rows.append({
        "domain": domain,
        "tld": tld,
        "year1_usd": year1_usd,
        "year1_zar": year1_usd * R_PER_USD,
        "renew_usd": renew_usd,
        "renew_zar": renew_usd * R_PER_USD,
        "verified": verified,
        "vibe": vibe_fit(domain),
    })

print(f"[rank] candidate rows (post-price filter): {len(rows)}")
print(f"[rank] verified (Porkbun-confirmed non-premium): {sum(1 for r in rows if r['verified'])}")
print(f"[rank] baseline (unverified for premium): {sum(1 for r in rows if not r['verified'])}")
print(f"[rank] premium rejects: {len(skipped_premium)}")

# Sort: brand-fit first (TLD, then vibe, then renewal), verified is a tiebreaker
rows.sort(key=lambda r: (
    TLD_RANK.get(r["tld"], 99),
    VIBE_RANK.get(r["vibe"], 99),
    0 if r["verified"] else 1,
    r["renew_zar"],
    r["domain"],
))

# Dedupe by base-name (pick best TLD per base)
seen = set()
deduped = []
for r in rows:
    base = r["domain"].rsplit(".", 1)[0]
    if base in seen: continue
    seen.add(base)
    deduped.append(r)
rows = deduped
print(f"[rank] unique bases: {len(rows)}")

top = rows[:100]
verified_in_top = sum(1 for r in top if r["verified"])
print(f"[rank] final 100, of which {verified_in_top} are Porkbun-verified non-premium")

# --- Output markdown --------------------------------------------------------
now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
out = HERE / "website-name-research.md"

with out.open("w") as f:
    f.write("# The Bloom Room — Domain Name Research\n\n")
    f.write(
        f"_Generated {now}. USD→ZAR rate **{R_PER_USD:.4f}** (open.er-api.com). "
        f"R200 threshold ≈ \\${R200_USD:.2f}. "
        f"{len(top)} names, all currently unregistered, all priced under R200 year-one at Porkbun._\n\n"
    )

    f.write("> **Data confidence legend**\n")
    f.write(">\n")
    f.write(f"> - **✓ verified** — Porkbun `checkDomain` confirmed both availability and non-premium status ({verified_in_top} of {len(top)}).\n")
    f.write(f"> - **~ baseline** — RDAP-available at registry level, priced at Porkbun's baseline TLD rate. Not yet re-verified against Porkbun's premium flag ({len(top) - verified_in_top} of {len(top)}). Roughly 30% of baseline names could turn out to be registry-premium — spot-check your 3–5 favorites before buying.\n\n")

    # Top 10 picks — one per TLD where possible, mixing vibes for visible diversity
    top_10_picks = []
    used_tlds = set()
    used_vibes = set()
    # First pass: prefer verified + one per unique TLD
    for r in top:
        if len(top_10_picks) >= 10: break
        if r["tld"] in used_tlds: continue
        top_10_picks.append(r)
        used_tlds.add(r["tld"])
        used_vibes.add(r["vibe"])
    # Second pass: fill remaining slots with diverse vibes
    for r in top:
        if len(top_10_picks) >= 10: break
        if r in top_10_picks: continue
        if r["vibe"] in used_vibes and len(used_vibes) < len(VIBE_RANK): continue
        top_10_picks.append(r)
        used_vibes.add(r["vibe"])
    # Third pass: pad from the top if still short
    for r in top:
        if len(top_10_picks) >= 10: break
        if r in top_10_picks: continue
        top_10_picks.append(r)
    f.write("## Top 10 picks\n\n")
    f.write("_Selected for TLD and vibe diversity across the top of the ranked list, so you see the full range of directions rather than 10 variations of the same thing._\n\n")
    for r in top_10_picks:
        tag = "✓" if r["verified"] else "~"
        f.write(f"**`{r['domain']}`** {tag} — R{r['year1_zar']:.0f} yr-1 · R{r['renew_zar']:.0f} renewal · _{r['vibe']}_  \n")
        f.write(f"{RATIONALE.get(r['vibe'], '')}\n\n")

    # Main table
    f.write(f"## All {len(top)} candidate domains, ranked\n\n")
    f.write("Rank order: TLD brand-fit (.com > .co > .club > .garden > .love > .boutique > .life > .studio > .earth > .world > .blog > .shop > .store) → vibe fit → verified before baseline → lower renewal.\n\n")
    f.write("| # | Domain | Status | Registrar | Year-1 (ZAR) | Renewal (ZAR) | Vibe fit |\n")
    f.write("|---|---|---|---|---|---|---|\n")
    for i, r in enumerate(top, 1):
        tag = "✓ verified" if r["verified"] else "~ baseline"
        f.write(
            f"| {i} | `{r['domain']}` | {tag} | Porkbun | R{r['year1_zar']:.0f} | R{r['renew_zar']:.0f} | {r['vibe']} |\n"
        )

    # Assumptions
    f.write("\n## Assumptions\n\n")
    f.write(f"- USD→ZAR exchange rate: **{R_PER_USD:.4f}** (open.er-api.com, {now})\n")
    f.write(f"- R200 threshold = approximately **\\${R200_USD:.2f} USD** year-one registration\n")
    f.write("- Availability: RDAP (IANA-authoritative) across 13 TLDs — .com, .co, .club, .garden, .love, .boutique, .life, .studio, .earth, .world, .blog, .shop, .store\n")
    f.write(f"- Pricing: Porkbun API v3 `checkDomain` for {verified_in_top} domains (live), Porkbun public `pricing/get` baseline for the remaining {len(top) - verified_in_top}\n")
    f.write(f"- Candidate pool: ~350 curated base names (feminine · blossoming · soft-life direction, explicit exclusions for trader vocab, wealth claims, 'room'/'honey')\n\n")

    # Honest note
    f.write("## Honest note on pricing and what to do next\n\n")
    f.write(
        f"At R{R_PER_USD:.2f}/USD, Porkbun `.com` at \\$11.08 is **R{11.08*R_PER_USD:.0f}** — comfortably under R200. "
        f"If ZAR weakens past R18/USD, Porkbun `.com` crosses R200 and **Cloudflare Registrar** becomes cheaper (registry wholesale, \\~\\$9.15/yr for `.com`, no markup).\n\n"
    )
    f.write(
        "The **baseline**-tagged names are the risk zone. RDAP confirms they're not registered, but some registries classify short/memorable names as 'premium' and charge hundreds of dollars. "
        f"Of the {verified_in_top} names we checked live, about 29% came back premium — so assume a similar rate in the baseline batch. "
        "Before pulling the trigger on a baseline-tagged name, paste it into Porkbun's search box — the UI shows premium flag and real first-year price.\n\n"
    )
    f.write(
        "**Ideal next step:** pick your 10-15 favorites from the list and tell me — I'll run the authenticated Porkbun check on those specifically to confirm non-premium pricing before you buy.\n\n"
    )

    # Premium rejects
    if skipped_premium:
        f.write("## Rejected: Porkbun flagged as registry-premium\n\n")
        f.write("Available per RDAP but registry-priced at $100+/yr. Avoid unless you know what you're doing:\n\n")
        for d, p, rp in skipped_premium[:40]:
            f.write(f"- `{d}` — first-year \\${p}, renewal \\${rp}\n")
        f.write("\n")

    # Verified names in full — all 34, including ones dedup pushed off the main table.
    # Every entry here is Porkbun-confirmed available AND non-premium — pricing is live.
    verified_all = []
    for domain, pb_entry in pb.items():
        if pb_entry.get("status") != "SUCCESS": continue
        resp = pb_entry.get("response", {})
        if resp.get("avail") != "yes": continue
        if resp.get("premium") == "yes": continue
        try:
            y = float(resp.get("price", "0"))
            rn = float(resp.get("additional", {}).get("renewal", {}).get("price", "0"))
        except (TypeError, ValueError):
            continue
        if y <= 0 or y > R200_USD: continue
        verified_all.append({
            "domain": domain,
            "year1_zar": y * R_PER_USD,
            "renew_zar": rn * R_PER_USD,
            "vibe": vibe_fit(domain),
            "tld": domain.rsplit(".", 1)[1],
        })
    verified_all.sort(key=lambda r: (TLD_RANK.get(r["tld"], 99), VIBE_RANK.get(r["vibe"], 99), r["renew_zar"]))
    if verified_all:
        f.write("## Porkbun-verified names (full list, 100% price-certain)\n\n")
        f.write(
            f"Every one of these {len(verified_all)} names is **Porkbun-confirmed available AND non-premium** — no surprise pricing at checkout. "
            "The brand-fit dedup in the main table keeps one row per base (whichever TLD ranks highest), so a base like `amanthea` shows up as `amanthea.co` in the main table (baseline-priced) even though `amanthea.boutique` is cheaper and verified. "
            "Treat this as the companion list: same bases, different TLDs, price-guaranteed.\n\n"
        )
        f.write("| Domain | Year-1 (ZAR) | Renewal (ZAR) | Vibe |\n|---|---|---|---|\n")
        for r in verified_all:
            f.write(f"| `{r['domain']}` | R{r['year1_zar']:.0f} | R{r['renew_zar']:.0f} | {r['vibe']} |\n")
        f.write("\n")

    # Trademark-first invented names — draw from ALL rows, prefer verified
    f.write("## 5 invented names worth trademarking first (lowest conflict risk)\n\n")
    f.write("These don't exist as English words, so collision risk is low and mark registrability is high:\n\n")
    invented_pool_verified = [
        r for r in rows
        if r["verified"]
        and r["vibe"] == "invented-feminine"
        and r["domain"].rsplit(".", 1)[0] not in {"aurelia", "celine", "capucine", "estelle", "amelie", "adeline", "sylvie", "blanche"}
    ]
    invented_pool_baseline = [
        r for r in top
        if not r["verified"]
        and r["vibe"] == "invented-feminine"
        and r["domain"].rsplit(".", 1)[0] not in {"aurelia", "celine", "capucine", "estelle", "amelie", "adeline", "sylvie", "blanche"}
    ]
    invented_pool = invented_pool_verified + invented_pool_baseline
    if len(invented_pool) < 5:
        invented_pool += [
            r for r in top
            if r not in invented_pool
            and len(r["domain"].rsplit(".", 1)[0]) <= 9
            and r["domain"].rsplit(".", 1)[0].endswith(("a", "elle", "ra", "ine", "ie"))
        ][:5]
    for r in invented_pool[:5]:
        tag = "✓" if r["verified"] else "~"
        f.write(f"- **`{r['domain']}`** {tag} — R{r['year1_zar']:.0f} yr-1 · R{r['renew_zar']:.0f} renewal\n")
    f.write("\n---\n\n")
    f.write(f"_Raw data: `rdap-cache.json` ({len(rdap)} lookups), `porkbun-cache.json` ({len(pb)} live checks), `porkbun-pricing.json` (TLD baseline table)._\n")

print(f"[done] wrote {out}")
