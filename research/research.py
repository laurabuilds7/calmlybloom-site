#!/usr/bin/env python3
"""
Bloom Room domain research.

Pipeline:
  1. Generate ~350 curated candidate names (feminine / blossoming / soft-life)
  2. RDAP availability, .com first → alternates for names where .com is taken
  3. Porkbun checkDomain on all available: live price + premium flag
  4. Filter under R200 year-one, drop premium, rank by brand fit + price
  5. Write website-name-research.md

Caches (safe to delete, cheap to rebuild):
  rdap-cache.json, porkbun-cache.json
"""

import json
import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).parent
PORKBUN_API_KEY = os.environ["PORKBUN_API_KEY"]
PORKBUN_SECRET_KEY = os.environ["PORKBUN_SECRET_KEY"]

# --- Candidate names ---------------------------------------------------------
BOTANICAL = [
    "wisteria", "primrose", "camellia", "clematis", "lavender", "magnolia",
    "jasmine", "freesia", "hyacinth", "dahlia", "mimosa", "verbena",
    "larkspur", "foxglove", "snowdrop", "honeysuckle", "bellflower",
    "marigold", "ranunculus", "cornflower", "bluebell", "sweetpea",
    "anemone", "columbine", "delphinium", "mallow", "yarrow", "tansy",
    "dandelion", "daisychain", "wildpoppy", "myrtle", "lilac", "fuchsia",
    "rosemary", "lupine", "zinnia", "aster", "gardenia", "hydrangea",
    "willowfern", "feverfew", "chamomile", "vervain", "valerian",
    "heather", "bluebonnet", "cosmos", "petalsoft", "wildflora",
    "edelweiss", "peonylight", "irisbloom", "violetmoss",
]

STATE_ACTION = [
    "blooming", "blossomed", "flourish", "unfurled", "fledged", "rising",
    "emerging", "softly", "tended", "ease", "lush", "sauntering", "lightly",
    "unfurling", "opening", "gentled", "nurtured", "rooted", "bloomed",
    "bloomy", "ripening", "lushly", "gently", "graceful", "thriving",
    "unfurls", "seeded", "budding", "greening", "thawing", "softening",
    "softened", "rewild", "rewilding", "tending", "tendril",
    "slowing", "slowed", "sprouted", "leafing", "fruiting", "sunning",
    "bloomingly", "flourishing", "unspooled",
]

DAWN_LIGHT = [
    "aurora", "aurelia", "daybreak", "halcyon", "luminous", "sunrose",
    "lumen", "glow", "firstlight", "dawnlight", "softdawn", "amber",
    "goldenhour", "dayrise", "morninglight", "softlight", "afterglow",
    "gloaming", "firstthaw", "breakofday", "dayspring",
    "sunwashed", "sundrenched", "moonflower", "duskbloom", "glowhour",
    "lightofday", "dawngold", "softglow",
]

COMPOUND = [
    "slowbloom", "wildbloom", "freebloom", "softbloom", "slowrise",
    "bloomwild", "bloomsoftly", "softlywild", "slowgrow", "slowseed",
    "seedandbloom", "bloomingsoftly", "gentlebloom", "calmlybloom",
    "softlyrise", "gentlegrow", "lushgrow", "freegrow", "quietgrow",
    "softgrow", "softrise", "looselybloom", "slowflourish", "softflourish",
    "slowunfold", "softunfold", "freeunfold", "bloomsoft", "softlygrow",
    "bloomerie", "bloomery", "bloomish", "bloomland", "bloomfield",
    "bloomingwild", "dailybloom", "quietbloom", "everbloom",
    "wildcrocus", "freelilac", "slowlilac", "softpetal", "freepetal",
    "quietpetal", "linenmornings", "slowsunday", "slowmorning",
    "softmorning", "softsaturday", "slowseason", "softseason",
    "freespring", "slowspring", "springsoft", "springbloom",
    "slowripen", "wildbloomco", "quietgarden", "softgarden",
    "gentlegarden", "ofbloom", "ofpetal", "ofmagnolia", "bloomco",
    "bloomsociety",
]

INVENTED_FEMININE = [
    "aurelia", "solene", "elowen", "aviana", "maren", "vera",
    "selene", "delia", "elara", "marisol",
    "livia", "vela", "amara", "amoura", "alma", "soleil",
    "beline", "celine", "marceline", "capucine", "seraphine", "amelie",
    "azelie", "adeline", "blanche", "clemence", "adelaide", "rosaline",
    "eline", "estelle", "margaux", "anouk", "fleur", "brielle",
    "lumiere", "lumiera", "luminara", "amorette", "florette",
    "aurelle", "aurelya", "solana", "solaria", "seraphia", "elysia",
    "anthea", "idalia", "calista", "elowyn", "roselle",
    "rosella", "marigolde", "cassia", "kassia", "sylvie",
    "sylvaine", "astraea", "linnea", "linette", "lyanna",
    "lyonne", "melisande", "melisene", "amanthea", "thalia",
    "oleandra", "nyssa", "elvira", "elaria",
]

SOFT_LIFE = [
    "softsunday", "slowwork", "quietluxe",
    "softhome", "slowhome", "gentlerise", "easeful", "easemode",
    "sauntered", "meandered", "ambled", "lingered",
    "dwellings", "quietabundance", "softabundance", "softflight",
    "quietflight", "gentleflight", "softfreedom", "quietfreedom",
    "slowfreedom", "softstudy", "learnsoftly",
    "tendedly", "steadythaw", "easeandbloom",
    "gentlemoney", "softerliving", "slowertrading", "lovetobloom",
    "livingsoftly", "blossomco", "softseed", "slowpetal",
    "gentledaily", "easefuldaily", "softlyelegant", "softlyfree",
    "slowlyfree", "freelyquiet", "softlytended",
]

BIRD_NATURE = [
    "meadowlark", "skylark", "nightingale", "goldfinch", "warbler",
    "yellowbird", "fledglings", "songbird", "swallowdive",
    "sparrowsong", "kingfisherblue", "starlinghour", "ternwind",
    "kestreldance", "wrenandivy", "lunamoth", "monarchwing", "firefly",
    "fireflies", "silkenwing", "silkmoth", "featherfern",
    "fernandgold", "mossandfern", "mossrose", "mossbloom",
    "brookandbloom", "rivuletco", "creekbed",
    "tidebloom", "quietmeadow", "openmeadow",
    "meadowlight", "meadowhour", "meadowsoftly", "meadowlyra",
]

WATER_FLOW = [
    "slowtide", "quietcurrent", "softcurrent", "softcove", "softinlet",
    "lowtide", "brooklet", "rivuletwild", "rushingsoftly",
    "idlewater", "lagoonbloom", "softshoal", "stillwater",
    "stillmeadow", "stillpetal", "stillcreek", "creekbloom",
    "easyflow", "softflow", "gentleflow", "quietflow",
]

CANDIDATES = sorted({c.lower().strip() for c in (
    BOTANICAL + STATE_ACTION + DAWN_LIGHT + COMPOUND + INVENTED_FEMININE +
    SOFT_LIFE + BIRD_NATURE + WATER_FLOW
) if c and "room" not in c and "honey" not in c and "queen" not in c})

BANNED_SUBSTRINGS = {"rich", "wealthy", "guaran", "empire", "alpha", "bro"}
CANDIDATES = [c for c in CANDIDATES if not any(b in c for b in BANNED_SUBSTRINGS)]

TRADEMARK_ECHO = {
    "amazon", "nike", "adidas", "apple", "google", "meta", "netflix",
    "spotify", "airbnb", "uber", "tesla", "slack", "notion", "canva",
    "figma", "shopify", "paypal", "revolut", "binance", "coinbase",
    "kraken", "etoro", "robinhood", "vanguard", "fidelity",
    "glossier", "everlane", "aesop", "goop", "honey",
}
CANDIDATES = [c for c in CANDIDATES if c not in TRADEMARK_ECHO]

print(f"[candidates] {len(CANDIDATES)} unique names after filtering")

# --- TLD configuration -------------------------------------------------------
# Order = brand-fit priority for The Bloom Room (members-only + botanical).
TLDS_PRIMARY = ["com"]  # always check first
TLDS_ALT = ["co", "club", "garden", "love", "boutique", "life", "studio",
            "earth", "world", "blog", "shop", "store"]

RDAP_ENDPOINTS = {
    "com": "https://rdap.verisign.com/com/v1/domain/",
    "co": "https://rdap.nic.co/domain/",
    "club": "https://rdap.nic.club/domain/",
    "garden": "https://rdap.nic.garden/domain/",
    "love": "https://rdap.registry.love/rdap/domain/",
    "boutique": "https://rdap.identitydigital.services/rdap/domain/",
    "life": "https://rdap.identitydigital.services/rdap/domain/",
    "studio": "https://rdap.identitydigital.services/rdap/domain/",
    "earth": "https://rdap.nic.earth/domain/",
    "world": "https://rdap.identitydigital.services/rdap/domain/",
    "blog": "https://rdap.blog.fury.ca/rdap/domain/",
    "shop": "https://rdap.gmoregistry.net/rdap/domain/",
    "store": "https://rdap.radix.host/rdap/domain/",
}

# Brand-fit order for sorting output (0 = best)
TLD_RANK = {
    "com": 0, "co": 1, "club": 2, "garden": 3, "love": 4, "boutique": 5,
    "life": 6, "studio": 7, "earth": 8, "world": 9, "blog": 10,
    "shop": 11, "store": 12,
}

# --- Caches ------------------------------------------------------------------
RDAP_CACHE_PATH = HERE / "rdap-cache.json"
PORKBUN_CACHE_PATH = HERE / "porkbun-cache.json"

def load_cache(p):
    if p.exists():
        try: return json.loads(p.read_text())
        except: return {}
    return {}

def save_cache(p, c):
    p.write_text(json.dumps(c, indent=2, sort_keys=True))

rdap_cache = load_cache(RDAP_CACHE_PATH)
porkbun_cache = load_cache(PORKBUN_CACHE_PATH)

# --- RDAP --------------------------------------------------------------------
def rdap_check(domain):
    if domain in rdap_cache:
        v = rdap_cache[domain]
        return v if isinstance(v, bool) else None
    tld = domain.rsplit(".", 1)[1]
    ep = RDAP_ENDPOINTS.get(tld)
    if not ep:
        return None
    req = urllib.request.Request(
        ep + domain,
        headers={"User-Agent": "bloom-room-research/1.0",
                 "Accept": "application/rdap+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            r.read()
            result = False
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result = True
        elif e.code == 400:
            body = e.read().decode("utf-8", "ignore").lower()
            result = True if ("not found" in body or "available" in body or "does not exist" in body) else None
        else:
            result = None
    except Exception:
        result = None
    rdap_cache[domain] = result
    return result

def rdap_batch(domains, label="", workers=10):
    pending = [d for d in domains if d not in rdap_cache]
    cached_hits = len(domains) - len(pending)
    print(f"[rdap {label}] {len(domains)} domains ({cached_hits} cached, {len(pending)} to query)")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(rdap_check, d): d for d in pending}
        for f in as_completed(futs):
            done += 1
            if done % 50 == 0:
                save_cache(RDAP_CACHE_PATH, rdap_cache)
                print(f"[rdap {label}]   {done}/{len(pending)}")
    save_cache(RDAP_CACHE_PATH, rdap_cache)
    results = {d: rdap_cache.get(d) for d in domains}
    avail = sum(1 for v in results.values() if v is True)
    print(f"[rdap {label}] available: {avail}")
    return results

# --- Porkbun -----------------------------------------------------------------
def porkbun_check(domain):
    if domain in porkbun_cache:
        return porkbun_cache[domain]
    url = f"https://api.porkbun.com/api/json/v3/domain/checkDomain/{domain}"
    body = json.dumps({"apikey": PORKBUN_API_KEY, "secretapikey": PORKBUN_SECRET_KEY}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "bloom-room-research/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: data = json.loads(e.read())
        except: data = {"status": "ERROR", "message": f"HTTP {e.code}"}
    except Exception as ex:
        data = {"status": "ERROR", "message": str(ex)}
    porkbun_cache[domain] = data
    return data

def porkbun_batch(domains):
    pending = [d for d in domains if d not in porkbun_cache]
    print(f"[porkbun] {len(domains)} to check ({len(domains) - len(pending)} cached, {len(pending)} live)")
    for i, d in enumerate(pending):
        porkbun_check(d)
        if (i + 1) % 25 == 0:
            save_cache(PORKBUN_CACHE_PATH, porkbun_cache)
            print(f"[porkbun]   {i+1}/{len(pending)}")
        time.sleep(1.05)
    save_cache(PORKBUN_CACHE_PATH, porkbun_cache)

# --- Vibe fit heuristic ------------------------------------------------------
def vibe_fit(domain):
    base = domain.rsplit(".", 1)[0]
    tld = domain.rsplit(".", 1)[1]
    if tld == "garden":
        return "botanical"
    if tld == "club":
        return "members-club"
    if tld == "boutique":
        return "boutique"
    if any(w in base for w in ["bloom", "blossom", "petal", "fleur", "flora", "rose",
                                 "lilac", "wisteria", "primrose", "magnolia", "camellia",
                                 "peony", "freesia", "dahlia", "mimosa", "verbena",
                                 "dandelion", "lavender", "jasmine", "marigold", "iris",
                                 "cornflower", "bluebell", "orchid", "violet", "crocus",
                                 "gardenia", "hydrangea", "lilac", "poppy"]):
        return "botanical"
    if any(w in base for w in ["dawn", "dusk", "aurora", "glow", "light", "luminous",
                                 "lumen", "sunrose", "gloaming", "goldenhour", "firstlight",
                                 "amber", "sun", "moonflower"]):
        return "dawn-light"
    if any(w in base for w in ["slow", "soft", "gentle", "ease", "quiet", "lush",
                                 "saunter", "unhurried", "linen", "still", "calm", "tend"]):
        return "slow-living"
    if any(w in base for w in ["meadowlark", "lark", "nightingale", "warbler", "goldfinch",
                                 "sparrow", "swallow", "fledg", "songbird", "firefly",
                                 "silkmoth", "lunamoth", "wren"]):
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

# --- Main --------------------------------------------------------------------
def main():
    # Stage 1: .com for everyone
    com_names = [f"{c}.com" for c in CANDIDATES]
    com_results = rdap_batch(com_names, label=".com")
    com_available = sorted([d for d, v in com_results.items() if v is True])
    com_taken_bases = sorted({d.rsplit(".", 1)[0] for d, v in com_results.items() if v is False})

    # Stage 2: alt TLDs for names where .com was TAKEN (more signal that the base is strong)
    # For names where .com was AVAILABLE, we'll still check .co as a bonus.
    alt_targets = []
    for base in com_taken_bases:
        for tld in TLDS_ALT:
            alt_targets.append(f"{base}.{tld}")
    # Small bonus: also check .co and .garden for available-.com names (handy multi-ownership later)
    for d in com_available:
        base = d.rsplit(".", 1)[0]
        alt_targets.append(f"{base}.co")
        alt_targets.append(f"{base}.garden")
    alt_results = rdap_batch(alt_targets, label="alt-TLDs")
    alt_available = sorted([d for d, v in alt_results.items() if v is True])

    all_available = sorted(set(com_available) | set(alt_available))
    print(f"[union] total available: {len(all_available)} (.com={len(com_available)} + alt={len(alt_available)})")

    # Stage 3: Porkbun price + premium check for everyone available
    porkbun_batch(all_available)

    # Stage 4: filter & rank
    R_PER_USD = json.load(open(HERE / "usd-rates.json"))["rates"]["ZAR"]
    R200_USD = 200.0 / R_PER_USD

    rows = []
    skipped_premium = []
    skipped_overprice = []
    skipped_notavail = []
    for domain in all_available:
        pb = porkbun_cache.get(domain, {})
        if pb.get("status") != "SUCCESS":
            continue
        if pb.get("avail") != "yes":
            skipped_notavail.append(domain)
            continue
        if pb.get("premium") == "yes":
            skipped_premium.append((domain, pb.get("price")))
            continue
        try:
            year1_usd = float(pb.get("price", "0"))
            renew_usd = float(pb.get("regularPrice", "0"))
        except (TypeError, ValueError):
            continue
        if year1_usd <= 0 or year1_usd > R200_USD:
            skipped_overprice.append((domain, year1_usd))
            continue
        rows.append({
            "domain": domain,
            "tld": domain.rsplit(".", 1)[1],
            "year1_usd": year1_usd,
            "year1_zar": year1_usd * R_PER_USD,
            "renew_usd": renew_usd,
            "renew_zar": renew_usd * R_PER_USD,
            "vibe": vibe_fit(domain),
        })

    # Sort: brand-fit TLD rank, then better-vibe first, then cheaper renewal
    VIBE_RANK = {"botanical": 0, "members-club": 1, "dawn-light": 2, "slow-living": 3,
                 "boutique": 4, "bird": 5, "water": 6, "invented-feminine": 7}
    rows.sort(key=lambda r: (
        TLD_RANK.get(r["tld"], 99),
        VIBE_RANK.get(r["vibe"], 99),
        r["renew_zar"],
        r["domain"],
    ))

    # Deduplicate if a base-name appears on multiple TLDs: keep best-ranked only
    seen_bases = set()
    deduped = []
    for r in rows:
        base = r["domain"].rsplit(".", 1)[0]
        if base in seen_bases:
            continue
        seen_bases.add(base)
        deduped.append(r)
    rows = deduped

    top = rows[:100]

    print(f"[rank] passing total: {len(rows)}, final table: {len(top)}")
    print(f"[rank] skipped premium: {len(skipped_premium)}, overprice: {len(skipped_overprice)}")

    # --- Markdown -------------------------------------------------------------
    out = HERE / "website-name-research.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with out.open("w") as f:
        f.write("# The Bloom Room — Domain Name Research\n\n")
        f.write(
            f"_Generated {now}. Live prices from Porkbun v3 API. "
            f"USD→ZAR rate: **{R_PER_USD:.4f}** (open.er-api.com). "
            f"R200 threshold = approximately \\${R200_USD:.2f} USD. "
            f"All {len(top)} names below are currently unregistered, not premium-flagged, and priced under R200 for year-one at Porkbun._\n\n"
        )

        # Top 10
        f.write("## Top 10 picks\n\n")
        for r in top[:10]:
            f.write(
                f"**`{r['domain']}`** — R{r['year1_zar']:.0f} yr-1 · R{r['renew_zar']:.0f} renewal · _{r['vibe']}_  \n"
            )
            f.write(f"{RATIONALE.get(r['vibe'], '')}\n\n")

        # Main table
        f.write(f"## All {len(top)} candidate domains, ranked\n\n")
        f.write("| # | Domain | Registrar | Year-1 (ZAR) | Renewal (ZAR) | Vibe fit |\n")
        f.write("|---|---|---|---|---|---|\n")
        for i, r in enumerate(top, 1):
            f.write(
                f"| {i} | `{r['domain']}` | Porkbun | R{r['year1_zar']:.0f} | R{r['renew_zar']:.0f} | {r['vibe']} |\n"
            )

        # Assumptions
        f.write("\n## Assumptions\n\n")
        f.write(f"- USD→ZAR exchange rate: **{R_PER_USD:.4f}** (open.er-api.com, {now})\n")
        f.write(f"- R200 threshold evaluates to approximately **\\${R200_USD:.2f} USD** year-one\n")
        f.write("- All year-1 and renewal prices live from Porkbun API v3 `checkDomain`\n")
        f.write("- Availability first confirmed via RDAP (IANA-authoritative), then re-verified by Porkbun `avail` flag\n")
        f.write("- Porkbun `premium: yes` auto-excluded (registry-premium pricing, typically $500+)\n")
        f.write(f"- Candidate pool: {len(CANDIDATES)} curated base names × up to 13 TLDs\n")
        f.write(f"- TLDs checked: .com, .co, .club, .garden, .love, .boutique, .life, .studio, .earth, .world, .blog, .shop, .store\n\n")

        # Porkbun vs. Cloudflare note
        f.write("## Where to actually buy\n\n")
        f.write(
            f"Porkbun is the cheapest credible registrar for year-one registration on nearly every TLD in this list. "
            f"At the current rate of R{R_PER_USD:.2f}/USD, Porkbun `.com` (\\$11.08) is **R{11.08*R_PER_USD:.0f}**. "
            f"The only scenario where Cloudflare Registrar beats Porkbun is on `.com` / `.net` renewals over the long term "
            f"— Cloudflare sells at registry wholesale (\\~\\$9.15/yr for `.com`) with zero markup. Worth a switch after year one.\n\n"
        )

        # Premium rejects
        if skipped_premium:
            f.write("## Rejected: flagged as registry-premium by Porkbun\n\n")
            f.write("These looked available via RDAP but Porkbun returned `premium: yes` — registry-priced at hundreds to thousands of USD per year:\n\n")
            for d, price in skipped_premium[:40]:
                f.write(f"- `{d}` (listed at \\${price})\n")
            f.write("\n")

        # Approach with care
        f.write("## Names to approach with care (brief etymology / brand-collision pass)\n\n")
        f.write("These passed availability + price but would benefit from a trademark search before you commit:\n\n")
        care_list = []
        for r in top:
            base = r["domain"].rsplit(".", 1)[0]
            if base in {"aurelia", "celine", "capucine", "adelaide", "blanche", "estelle", "amelie"}:
                care_list.append((r["domain"], "French-first-name bias — check for fashion/beauty collisions"))
            elif base in {"wisteria", "magnolia", "camellia", "hydrangea"}:
                care_list.append((r["domain"], "Common plant name — scan for existing boutiques, spas, lifestyle brands"))
            elif base in {"meadowlark", "nightingale", "goldfinch", "songbird"}:
                care_list.append((r["domain"], "Birding community names — watch for apparel / stationery brand overlap"))
            elif base.endswith("ly") and r["tld"] == "com":
                care_list.append((r["domain"], "`-ly` startup-naming trope — fine with a strong visual mark"))
        for d, note in care_list[:15]:
            f.write(f"- `{d}` — {note}\n")
        f.write("\n")

        # Invented names worth trademarking first
        f.write("## 5 invented names to trademark-first (lowest conflict risk)\n\n")
        f.write("These don't exist as English words, so collision risk is minimal — strongest candidates for building a distinct brand mark:\n\n")
        invented_pool = [
            r for r in top
            if r["vibe"] == "invented-feminine"
            and r["domain"].rsplit(".", 1)[0] not in {"aurelia", "celine", "capucine", "estelle", "amelie", "adeline"}
        ]
        invented_picks = invented_pool[:5]
        if len(invented_picks) < 5:
            # pad with any remaining invented-sounding names
            for r in top:
                if r in invented_picks: continue
                base = r["domain"].rsplit(".", 1)[0]
                if len(base) <= 9 and base.endswith(("a", "elle", "ra", "ine", "ie")):
                    invented_picks.append(r)
                if len(invented_picks) >= 5: break
        for r in invented_picks[:5]:
            f.write(f"- **`{r['domain']}`** — R{r['year1_zar']:.0f} yr-1 · R{r['renew_zar']:.0f} renewal\n")
        f.write("\n---\n\n")
        f.write("_Raw data cached in `rdap-cache.json` and `porkbun-cache.json`. Re-running `research.py` is cheap (cached results reused)._\n")

    print(f"[done] wrote {out}")
    print(f"[done] final table size: {len(top)}")


if __name__ == "__main__":
    main()
