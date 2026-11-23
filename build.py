#!/usr/bin/env python3
"""Static site generator for torontocookies.ca (no dependencies, Python 3.8+).

Usage:
  python3 build.py          # (re)generate every page and config file in place
  python3 build.py --check  # QA: required files, JSON-LD parses, internal links resolve,
                            #     one <h1>, title/description lengths, no unreplaced tokens

Edit CONFIG / PACKAGES / FAQ below, re-run, commit. Hostinger serves the repo root.
"""
import json, os, re, sys, html
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://torontocookies.ca"
TODAY = "2026-11-23"

CONFIG = {
    # Where order/inquiry form submissions go (FormSubmit.co, free, no account).
    # The first submission triggers a one-time activation email to this address.
    "ORDER_EMAIL": "orders@torontocookies.ca",
    # PostHog project "Default project" (593979). Public client token, safe in HTML.
    "POSTHOG_KEY": "phc_sKd9PxBNJ2WvbEzjkErxoSaaoBCikwiSHFm4xSyjnF9r",
    "POSTHOG_HOST": "https://us.i.posthog.com",
    "ORDER_BY": "Wednesday, December 9, 2026",
    "DELIVER_BY": "Friday, December 18, 2026",
}

# >>> STRIPE PAYMENT LINK PLACEHOLDERS <<<
# Live Stripe Payment Links (Builtbylt account, CAD, no tax), created Nov 23, 2026.
# After payment Stripe redirects to /thanks/?paid=<package>&session_id=...
# An empty value makes that package's button fall back to the inquiry form.
STRIPE_LINKS = {
    "single-gift": "https://buy.stripe.com/cNidR87XF4IRgj69y29ws02",       # plink_1Uf2EPAknPcpAXyTnyLcULq1, $59 CAD
    "office-tray": "https://buy.stripe.com/eVq3cua5N2AJgj6dOi9ws03",       # plink_1Uf2EYAknPcpAXyTrr3AN935, $129 CAD
    "client-gift-pack": "https://buy.stripe.com/6oUcN45Px3EN7MA7pU9ws04",  # plink_1Uf2EdAknPcpAXyTuovy1Sf3, $590 CAD
    "logo-cookies": "",       # Custom quote -> Stripe Invoice, never a fixed link
}

PACKAGES = [
    {
        "id": "single-gift", "slug": "holiday-cookie-gift-box-toronto",
        "name": "Single Holiday Cookie Gift", "price": 59, "price_label": "$59",
        "kw": "Holiday cookie gift box delivered in Toronto",
        "short": "One festive box of 6 gourmet cookies from a top Toronto bakery, with a handwritten-style card, delivered to one Toronto address.",
        "includes": ["6 gourmet holiday cookies, individually chosen for the recipient",
                     "Gift box with ribbon and a personalized card message",
                     "Delivery to one address in the City of Toronto",
                     "Nut-free option on request (sourced from a nut-free bakery)"],
        "best_for": "A thank-you to one client, a host gift, or a colleague you can't see in person.",
        "image": "/assets/gift-box.webp", "iw": 933, "ih": 933,
        "alt": "A tall stack of chocolate chip cookies",
    },
    {
        "id": "office-tray", "slug": "office-cookie-tray-toronto",
        "name": "Office Holiday Cookie Tray", "price": 129, "price_label": "$129",
        "kw": "Office holiday party cookie tray in Toronto",
        "short": "A shareable tray of 24 to 30 fresh cookies for the office, the holiday party, or a client meeting, delivered to your Toronto office.",
        "includes": ["24 to 30 assorted fresh cookies (about 2 per person for a team of 12 to 15)",
                     "Platter or gift-box presentation, ready to put out",
                     "Delivery to one Toronto office, timed to your event",
                     "Dietary notes (nut-free, vegan options) passed to the bakery"],
        "best_for": "Holiday parties, team lunches, reception desks and client meetings.",
        "image": "/assets/office-tray.webp", "iw": 1000, "ih": 1000,
        "alt": "A parchment-lined bowl filled with chocolate chip cookies to share",
    },
    {
        "id": "client-gift-pack", "slug": "client-cookie-gift-pack-toronto",
        "name": "Client Gift Pack (10 boxes)", "price": 590, "price_label": "$590",
        "kw": "Corporate client cookie gifts, 10 recipients in Toronto",
        "short": "Ten holiday cookie gift boxes sent to ten different Toronto addresses, each with its own card. Send us a list; we handle the rest.",
        "includes": ["10 gift boxes of 6 gourmet holiday cookies",
                     "10 personalized cards (your message, each recipient's name)",
                     "Delivery to up to 10 different City of Toronto addresses",
                     "One delivery-status summary email when every box has landed",
                     "Need 20, 50 or 100? Add packs or ask for a quote"],
        "best_for": "Law, accounting, real-estate and agency teams thanking their best clients.",
        "image": "/assets/client-gifts.webp", "iw": 933, "ih": 933,
        "alt": "Gingerbread people and snowflake cookies cooling on a rack",
    },
    {
        "id": "logo-cookies", "slug": "logo-cookies-toronto",
        "name": "Custom Logo Cookies", "price": 79, "price_label": "Bakery cost + 20% (from $79)",
        "kw": "Custom logo cookies in Toronto for corporate gifts and events",
        "short": "Cookies printed or hand-decorated with your company logo, sourced from a Toronto logo-cookie specialist. We quote the bakery's price plus a 20% concierge fee, minimum $79.",
        "includes": ["Free design mock-up from the bakery before you commit",
                     "Printed (edible ink) or hand-iced logo cookies, individually wrapped",
                     "Optional gift boxes, cards and multi-address delivery",
                     "Transparent pricing: bakery quote + 20% concierge fee, $79 minimum"],
        "best_for": "Client gifts, conferences, launches and holiday parties where your brand should show.",
        "image": "/assets/logo-cookies.webp", "iw": 1000, "ih": 1000,
        "alt": "Iced sugar cookies in stars, trees, and a heart, with sprinkles",
    },
]

HERO = {"src": "/assets/hero.webp", "w": 1200, "h": 800,
        "srcset": "/assets/hero-800.webp 800w, /assets/hero.webp 1200w",
        "sizes": "(min-width: 800px) 42vw, 100vw",
        "alt": "Wrapped gift boxes with satin ribbons, arranged as a corporate gift"}

FAQ = [
    ("How does Toronto Cookies work?",
     "Tell us who the cookies are for, when they need to arrive and your budget. We pick the right licensed Toronto bakery, confirm availability and price, and send you a secure payment link. Once you've paid, we place the order, add your cards and coordinate delivery to every address."),
    ("Who bakes the cookies?",
     "Established, inspected Toronto bakeries. Toronto Cookies is a gifting concierge: we never bake or handle food ourselves. We match each order to a bakery that suits it, for example a nut-free facility or a logo-cookie specialist."),
    ("How much do corporate cookie gifts cost in Toronto?",
     "Our packages are $59 for a single gift box delivered in Toronto, $129 for an office tray of 24 to 30 cookies, and $590 for ten client gift boxes sent to ten addresses. Custom logo cookies are the bakery's price plus a 20% concierge fee, with a $79 minimum. Prices are in Canadian dollars."),
    ("What's the deadline to order holiday cookie gifts for 2026?",
     "Order by " + CONFIG["ORDER_BY"] + " for delivery by " + CONFIG["DELIVER_BY"] + ". Later orders are handled on a best-effort basis depending on bakery capacity, so ask as early as you can."),
    ("Can you deliver to multiple addresses?",
     "Yes. The Client Gift Pack covers ten different City of Toronto addresses, and larger lists are quoted. Send a spreadsheet or a simple list of names, addresses and card messages."),
    ("Do you have nut-free or allergy-friendly options?",
     "Yes. On request we source from a dedicated nut-free bakery, and vegan options are available. Allergen information always comes from the bakery's own labels; we pass your dietary notes on but cannot guarantee against cross-contact."),
    ("Can I put my company logo on the cookies?",
     "Yes. Logo cookies are printed with edible ink or hand-iced by a Toronto specialist bakery, usually with a free mock-up first. Most bakeries need around 50 cookies per design and 3 to 9 business days. We quote bakery cost plus 20%, minimum $79."),
    ("How do I pay?",
     "After we confirm your order, you pay by card through a secure Stripe payment link or invoice. Nothing is ordered from the bakery until your payment is complete."),
    ("Where do you deliver?",
     "Delivery within the City of Toronto is included in the package prices. Elsewhere in the GTA (Mississauga, Markham, Vaughan, Richmond Hill and more) is quoted per order."),
    ("What if something goes wrong?",
     "You can cancel free of charge until we place the bakery order. If we can't fulfil an order as confirmed, you get a full refund. If a box arrives damaged, send a photo the same day and we'll make it right with the bakery."),
]

NAV = [("/", "Home"), ("/corporate-cookie-gifts-toronto/", "Corporate gifts"),
       ("/faq/", "FAQ"), ("/order/", "Order / quote")]

LEGACY_HTML = r'''<html>
    <head>
        <!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@3.4.1/dist/css/bootstrap.min.css" integrity="sha384-HSMxcRTRxnN+Bdg0JdbxYKrThecOKuH5zCYotlSAcp1+c8xmyTe9GYg1l9a69psu" crossorigin="anonymous">

<!-- Optional theme -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@3.4.1/dist/css/bootstrap-theme.min.css" integrity="sha384-6pzBo3FDv/PJ8r2KRkGHifhEocL+1X2rVCTTkUfGk7/0pbek5mMa1upzvWbrUbOZ" crossorigin="anonymous">

<!-- Latest compiled and minified JavaScript -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@3.4.1/dist/js/bootstrap.min.js" integrity="sha384-aJ21OjlMXNL5UyIl/XNwTMqvzeRMZH2w8c5cRVpzpU8Y5bApTppSuUkhZXN0VxHd" crossorigin="anonymous"></script>
        <title>Greystone Toronto Cookies</title>
    </head>
    <body>
        <header></header>
        <div class="wrapper">
            <div class="container">
                <div class="row">
                    <div class="col-md-12">
                        <img src="assets/torontocookies.jpg" style="width: 100%; max-width: 180px;"/>
                        <h1>Toronto Cookies</h1>
                            <div class="content">
                            Email to use: greystone@torontocookies.ca<br/>
                            <br/>
                            <a href="mail.hostinger.com">mail.hostinger.com</a>
                        </div>
                        <br/>
                        <div class="content">
                            Responsible for <a href="https://www.instagram.com/torontocookies_ca/" target="_blank">IG</a> --> Lilia, Alessandra, Diego<br/>
                            Responsible for <a href="https://www.facebook.com/torontocookies.ca" target="_blank">FB</a> --> Vini, Sacha, Santiago<br/>
                            Responsible for <a href="https://www.tiktok.com/@torontocookies.ca" target="_blank">Tiktok</a> --> Dogac, Jane, JJ
                        </div>

                    </div>
                </div>
            </div>
        </div>
    </body>
</html>
'''

e = html.escape

# ---------------------------------------------------------------- schema helpers
ORG = {
    "@type": ["Organization", "ProfessionalService"], "@id": BASE + "/#org",
    "name": "Toronto Cookies", "url": BASE + "/", "logo": BASE + "/assets/logo.png",
    "image": BASE + "/assets/logo.png",
    "description": "Corporate and holiday cookie gifting concierge for Toronto offices. We source from licensed Toronto bakeries and deliver to every recipient.",
    "email": CONFIG["ORDER_EMAIL"], "priceRange": "$59-$590+",
    "areaServed": [{"@type": "City", "name": "Toronto"}, {"@type": "AdministrativeArea", "name": "Greater Toronto Area"}],
    "address": {"@type": "PostalAddress", "addressLocality": "Toronto", "addressRegion": "ON", "addressCountry": "CA"},
    "sameAs": ["https://www.instagram.com/torontocookies_ca/", "https://www.facebook.com/torontocookies.ca", "https://www.tiktok.com/@torontocookies.ca"],
}
WEBSITE = {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": "Toronto Cookies", "publisher": {"@id": BASE + "/#org"}, "inLanguage": "en-CA"}

def crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (u, n) in enumerate(items)]}

def faq_schema(pairs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}

def product_schema(p):
    url = BASE + "/" + p["slug"] + "/"
    offer = {"@type": "Offer", "priceCurrency": "CAD", "price": str(p["price"]), "url": url,
             "availability": "https://schema.org/InStock", "priceValidUntil": "2026-12-31",
             "seller": {"@id": BASE + "/#org"},
             "areaServed": {"@type": "City", "name": "Toronto"}}
    if p["id"] == "logo-cookies":
        offer["priceSpecification"] = {"@type": "PriceSpecification", "minPrice": "79", "priceCurrency": "CAD",
                                       "description": "Bakery quote plus 20% concierge fee, $79 minimum"}
    return {"@type": "Product", "@id": url + "#product", "name": p["name"], "description": p["short"],
            "image": BASE + "/assets/logo.png", "brand": {"@type": "Brand", "name": "Toronto Cookies"},
            "category": "Corporate cookie gifts", "offers": offer}

# ---------------------------------------------------------------- layout
POSTHOG = """<script>
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group getSurveys onSessionId".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
posthog.init('%s',{api_host:'%s',person_profiles:'identified_only'});
posthog.register({site:'torontocookies.ca',site_env:(location.hostname.indexOf('staging.')===0?'staging':'production')});
</script>""" % (CONFIG["POSTHOG_KEY"], CONFIG["POSTHOG_HOST"])

# Staging guard: adds <meta name="robots" content="noindex,nofollow"> on staging.* hosts.
# The authoritative noindex is the X-Robots-Tag header set in .htaccess for staging.*.
STAGING_GUARD = """<script>if(location.hostname.indexOf('staging.')===0){var m=document.createElement('meta');m.name='robots';m.content='noindex,nofollow';document.head.appendChild(m);}</script>"""

def page(path, title, desc, body, schema_nodes, h_crumbs=None, preload=None, bleed=False, preload_srcset=None, preload_sizes=None):
    canonical = BASE + path
    graph = [ORG, WEBSITE] + schema_nodes
    if h_crumbs:
        graph.append(crumbs(h_crumbs))
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    nav = "".join('<a href="%s"%s>%s</a>' % (u, ' aria-current="page"' if u == path else "", n) for u, n in NAV)
    if preload and preload_srcset:
        preload_tag = ('<link rel="preload" as="image" href="%s" imagesrcset="%s" imagesizes="%s" fetchpriority="high">'
                       % (preload, preload_srcset, preload_sizes))
    elif preload:
        preload_tag = '<link rel="preload" as="image" href="%s" fetchpriority="high">' % preload
    else:
        preload_tag = ""
    main_attr = "" if bleed else ' class="wrap page"'
    return f"""<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
{STAGING_GUARD}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Toronto Cookies">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/assets/logo.png">
<meta property="og:locale" content="en_CA">
<meta name="twitter:card" content="summary">
<link rel="icon" href="/assets/logo.png" type="image/png">
{preload_tag}
<link rel="stylesheet" href="/assets/site.css?v=6">
<script type="application/ld+json">
{ld}
</script>
{POSTHOG}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="announce"><div class="wrap"><p>Order by {CONFIG["ORDER_BY"]} for delivery by {CONFIG["DELIVER_BY"]}.</p></div></div>
<header class="site-header"><div class="wrap">
<a class="brand" href="/">Toronto Cookies</a>
<nav aria-label="Main">{nav}</nav>
</div></header>
<main id="main"{main_attr}>
{body}
</main>
<footer class="site-footer"><div class="wrap">
<p class="footer-brand">Toronto Cookies</p>
<p>A corporate and holiday cookie gifting concierge for Toronto and the GTA. We source from licensed, inspected Toronto bakeries. We do not bake or handle food ourselves.</p>
<nav aria-label="Footer">
<a href="/holiday-cookie-gift-box-toronto/">Single gift $59</a>
<a href="/office-cookie-tray-toronto/">Office tray $129</a>
<a href="/client-cookie-gift-pack-toronto/">Client pack $590</a>
<a href="/logo-cookies-toronto/">Logo cookies</a>
<a href="/guides/holiday-cookie-gift-deadlines-toronto-2026/">2026 order deadlines</a>
<a href="/custom-cookie-prices-toronto/">Toronto cookie price guide</a>
<a href="/about/">About</a>
<a href="/faq/">FAQ</a>
<a href="/order/">Order</a>
</nav>
<p class="fine">Questions: <a href="mailto:{CONFIG['ORDER_EMAIL']}">{CONFIG['ORDER_EMAIL']}</a> · Prices in CAD · © 2026 Toronto Cookies</p>
</div></footer>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""

def pay_button(p):
    link = STRIPE_LINKS.get(p["id"], "")
    if link:
        return f'<a class="btn" href="{e(link)}" data-track="pay_link_clicked" data-package="{p["id"]}">Pay {e(p["price_label"])} securely</a>'
    # STRIPE PLACEHOLDER: no payment link yet, so route to the inquiry form instead.
    return (f'<!-- STRIPE_PAYMENT_LINK_PLACEHOLDER:{p["id"]} - set STRIPE_LINKS["{p["id"]}"] in build.py -->'
            f'<a class="btn" href="/order/?package={p["id"]}" data-track="package_cta_clicked" data-package="{p["id"]}">Request this package</a>')

def card(p):
    return f"""<article class="card">
<img src="{p['image']}" alt="{e(p['alt'])}" width="{p['iw']}" height="{p['ih']}" loading="lazy" decoding="async">
<div class="card-body">
<h3><a href="/{p['slug']}/">{e(p['name'])}</a></h3>
<p class="price">{e(p['price_label'])}<span> CAD</span></p>
<p>{e(p['short'])}</p>
<p><a class="btn btn-small" href="/{p['slug']}/" data-track="package_viewed_from_card" data-package="{p['id']}">See what's included</a></p>
</div>
</article>"""

def faq_html(pairs):
    return "\n".join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in pairs)

DEADLINE = f'<p class="notice"><strong>2026 holiday deadline:</strong> order by {CONFIG["ORDER_BY"]} for delivery by {CONFIG["DELIVER_BY"]}.</p>'

# ---------------------------------------------------------------- pages
def build_pages():
    out = {}
    cards = "\n".join(card(p) for p in PACKAGES)

    # Home
    logo = next(p for p in PACKAGES if p["id"] == "logo-cookies")
    body = f"""<section class="hero"><div class="wrap hero-grid">
<div>
<h1>Corporate cookie gifts for Toronto teams and clients</h1>
<p class="lede">Client gifts, office trays, holiday thank-yous and logo cookies, delivered across the GTA.</p>
<p class="cta-row"><a class="btn" href="/order/" data-track="hero_cta_clicked">Order corporate gifts</a> <a class="btn btn-ghost" href="#packages">See packages</a></p>
</div>
<figure class="hero-visual"><img src="{HERO['src']}" srcset="{HERO['srcset']}" sizes="{HERO['sizes']}" alt="{e(HERO['alt'])}" width="{HERO['w']}" height="{HERO['h']}" fetchpriority="high" decoding="async"></figure>
</div></section>
<section class="proof" aria-label="Ordering facts"><div class="wrap">
<p>Prepaid via Stripe · City of Toronto delivery included, GTA quoted · Order by {CONFIG["ORDER_BY"]}</p>
</div></section>
<section class="trust" aria-label="Why offices use Toronto Cookies">
<div class="wrap">
<ul class="trust-row">
<li><strong>Licensed bakeries</strong><span>Inspected Toronto kitchens. We never bake or handle the food.</span></li>
<li><strong>One list, every address</strong><span>Ten clients across the city, without ten bakery checkouts.</span></li>
<li><strong>Pay after we confirm</strong><span>Nothing is ordered until you approve the bakery and the price.</span></li>
<li><strong>A card in every box</strong><span>Your message, each recipient's name, delivered with the cookies.</span></li>
</ul>
</div>
</section>
<section id="packages" class="band"><div class="wrap">
<h2>Gift packages</h2>
<p class="section-lead">Fixed prices in Canadian dollars. City of Toronto delivery is included.</p>
<div class="grid">{cards}</div>
</div></section>
<section class="how"><div class="wrap">
<h2>How it works</h2>
<ol class="steps steps-3">
<li><h3>Tell us the brief</h3><p>Who it's for, how many, the delivery date, your budget and any dietary needs.</p></li>
<li><h3>Confirm, then pay</h3><p>We reply within one business day with the bakery and final price. You pay by card. Nothing is ordered before that.</p></li>
<li><h3>Every box lands</h3><p>We add your cards, book delivery, and email you once when every recipient has their cookies.</p></li>
</ol>
</div></section>
<section class="upsell"><div class="wrap upsell-grid">
<img src="{logo['image']}" alt="{e(logo['alt'])}" width="{logo['iw']}" height="{logo['ih']}" loading="lazy" decoding="async">
<div>
<h2>Cookies with your logo</h2>
<p>Printed in edible ink or hand-iced by a Toronto specialist, usually with a free mock-up first. The price is the bakery's quote plus a 20% concierge fee, from $79.</p>
<p><a class="btn" href="/logo-cookies-toronto/" data-track="package_viewed_from_card" data-package="logo-cookies">See logo cookies</a></p>
</div>
</div></section>
<section class="deadline"><div class="wrap">{DEADLINE}</div></section>
<section class="faq-teaser"><div class="wrap">
<h2>Common questions</h2>
{faq_html(FAQ[:5])}
<p class="after-list"><a class="text-link" href="/faq/">All questions</a></p>
</div></section>"""
    out["index.html"] = page("/", "Corporate & Holiday Cookie Gifts Toronto | Toronto Cookies",
        "Corporate and holiday cookie gifts delivered across Toronto from top local bakeries. Single gifts $59, office trays $129, 10 client gifts $590. Order by Dec 9.",
        body, [faq_schema(FAQ[:5])] + [product_schema(p) for p in PACKAGES],
        preload="/assets/hero-800.webp", bleed=True, preload_srcset=HERO["srcset"], preload_sizes=HERO["sizes"])

    # Corporate hub
    body = f"""<h1>Corporate cookie gifts in Toronto</h1>
<p class="lede"><strong>The easiest way to send cookie gifts to Toronto clients and staff:</strong> choose a package ($59 single gift, $129 office tray, $590 for ten clients, or custom logo cookies), send one list, and Toronto Cookies coordinates a licensed Toronto bakery, personalized cards and delivery to every address.</p>
{DEADLINE}
<h2>Packages</h2>
<div class="grid">{cards}</div>
<h2>Popular uses</h2>
<ul>
<li><strong>Client appreciation:</strong> law, accounting, real estate, wealth and agency teams thanking top accounts before the holidays.</li>
<li><strong>Employee gifts:</strong> boxes sent to remote and hybrid staff at home.</li>
<li><strong>Office holiday party:</strong> a tray for the team, timed to your event.</li>
<li><strong>Branded moments:</strong> logo cookies for launches, conferences and year-end mailers.</li>
</ul>
<h2>What it costs</h2>
<table><thead><tr><th>Package</th><th>Price (CAD)</th><th>Recipients</th></tr></thead><tbody>
<tr><td><a href="/holiday-cookie-gift-box-toronto/">Single holiday gift</a></td><td>$59</td><td>1 address</td></tr>
<tr><td><a href="/office-cookie-tray-toronto/">Office tray (24–30 cookies)</a></td><td>$129</td><td>1 office</td></tr>
<tr><td><a href="/client-cookie-gift-pack-toronto/">Client gift pack</a></td><td>$590</td><td>10 addresses</td></tr>
<tr><td><a href="/logo-cookies-toronto/">Custom logo cookies</a></td><td>Bakery cost + 20%, min $79</td><td>Any</td></tr>
</tbody></table>
<p>City of Toronto delivery included. GTA quoted. <a href="/custom-cookie-prices-toronto/">How these compare with Toronto bakery prices</a>.</p>
<p><a class="btn" href="/order/" data-track="hub_cta_clicked">Start an order</a></p>
<h2>Questions</h2>{faq_html(FAQ[1:7])}"""
    out["corporate-cookie-gifts-toronto/index.html"] = page("/corporate-cookie-gifts-toronto/",
        "Corporate Cookie Gifts Toronto: Clients & Staff | Toronto Cookies",
        "Send corporate cookie gifts to Toronto clients and staff: $59 single gifts, $129 office trays, $590 for 10 clients, custom logo cookies. One list, every address.",
        body, [faq_schema(FAQ[1:7])], [("/", "Home"), ("/corporate-cookie-gifts-toronto/", "Corporate cookie gifts")])

    # Package pages
    for p in PACKAGES:
        path = "/" + p["slug"] + "/"
        pfaq = [FAQ[3], FAQ[7], FAQ[8], FAQ[5]]
        if p["id"] == "logo-cookies":
            pfaq = [FAQ[6], FAQ[3], FAQ[7], FAQ[8]]
        inc = "".join(f"<li>{e(i)}</li>" for i in p["includes"])
        body = f"""<div class="product-intro">
<figure class="product-photo"><img src="{p['image']}" alt="{e(p['alt'])}" width="{p['iw']}" height="{p['ih']}" fetchpriority="high" decoding="async"></figure>
<div>
<p class="crumbs"><a href="/">Home</a> › <a href="/corporate-cookie-gifts-toronto/">Corporate gifts</a> › {e(p['name'])}</p>
<h1>{e(p['kw'])}</h1>
<p class="lede"><strong>{e(p['name'])}: {e(p['price_label'])} CAD.</strong> {e(p['short'])}</p>
<div class="buy">{pay_button(p)} <a class="btn btn-ghost" href="/order/?package={p['id']}" data-track="quote_cta_clicked" data-package="{p['id']}">Ask a question first</a></div>
{DEADLINE}
</div>
</div>
<h2>What's included</h2><ul>{inc}</ul>
<h2>Best for</h2><p>{e(p['best_for'])}</p>
<h2>How ordering works</h2>
<ol class="order-steps"><li>Send the order form (2 minutes).</li><li>We confirm the bakery, date and final price within one business day.</li><li>You pay by card through a secure Stripe link. Nothing is ordered before payment.</li><li>We place the order, add cards and confirm delivery.</li></ol>
<h2>Questions</h2>{faq_html(pfaq)}
<p class="after-list">Other packages: {' · '.join(f'<a href="/{q["slug"]}/">{e(q["name"])}</a>' for q in PACKAGES if q is not p)}</p>"""
        title = {"single-gift": "Holiday Cookie Gift Box Delivered in Toronto ($59) | Toronto Cookies",
                 "office-tray": "Office Cookie Tray Toronto for Holiday Parties ($129)",
                 "client-gift-pack": "Client Cookie Gifts Toronto: 10 Boxes, 10 Addresses ($590)",
                 "logo-cookies": "Custom Logo Cookies Toronto for Corporate Gifts | Toronto Cookies"}[p["id"]]
        desc = p["short"][:155].rsplit(" ", 1)[0] + "."
        out[p["slug"] + "/index.html"] = page(path, title, desc, body, [product_schema(p), faq_schema(pfaq)],
            [("/", "Home"), ("/corporate-cookie-gifts-toronto/", "Corporate cookie gifts"), (path, p["name"])],
            preload=p["image"])

    # Order / inquiry form
    opts = "".join(f'<option value="{p["id"]}">{e(p["name"])} ({e(p["price_label"])})</option>' for p in PACKAGES)
    body = f"""<h1>Order or request a quote</h1>
<p class="lede">Tell us what you need. We reply within one business day with the bakery, delivery date and final price, plus a secure payment link. <strong>You're not charged until you approve.</strong></p>
{DEADLINE}
<form class="order" action="https://formsubmit.co/{CONFIG['ORDER_EMAIL']}" method="POST" data-track-form="quote_submitted">
<input type="hidden" name="_subject" value="New Toronto Cookies order request">
<input type="hidden" name="_next" value="{BASE}/thanks/">
<input type="hidden" name="_template" value="table">
<input type="text" name="_honey" class="hp" tabindex="-1" autocomplete="off">
<label>Package<select name="package" id="package" required><option value="">Choose one</option>{opts}<option value="not-sure">Not sure yet, help me choose</option></select></label>
<label>Your name<input name="name" autocomplete="name" required></label>
<label>Company<input name="company" autocomplete="organization"></label>
<label>Email<input type="email" name="email" autocomplete="email" required></label>
<label>Phone (optional)<input type="tel" name="phone" autocomplete="tel"></label>
<label>How many recipients or cookies?<input name="quantity" placeholder="e.g. 10 clients, or 1 tray for 15 people"></label>
<label>Delivery date needed<input type="date" name="delivery_date" min="2026-11-24"></label>
<label>Delivery area<select name="area"><option>City of Toronto</option><option>Elsewhere in the GTA</option><option>Mix of both</option></select></label>
<label>Dietary needs<select name="dietary"><option>None</option><option>Nut-free</option><option>Vegan</option><option>Other (add in notes)</option></select></label>
<label>Budget per recipient (optional)<input name="budget" placeholder="e.g. $50 to $75"></label>
<label>Notes: recipients, card message, logo, anything else<textarea name="notes" rows="5"></textarea></label>
<button class="btn" type="submit">Send my request</button>
<p class="small">Prefer email? Write to <a href="mailto:{CONFIG['ORDER_EMAIL']}?subject=Cookie%20gift%20order">{CONFIG['ORDER_EMAIL']}</a>. We use your details only to handle this order.</p>
</form>"""
    out["order/index.html"] = page("/order/", "Order Corporate Cookie Gifts in Toronto | Toronto Cookies",
        "Request corporate or holiday cookie gifts in Toronto. Share recipients, date and budget; we confirm bakery and price in one business day. No charge until you approve.",
        body, [], [("/", "Home"), ("/order/", "Order")])

    out["thanks/index.html"] = page("/thanks/", "Thanks, we've got your request | Toronto Cookies",
        "Thanks for your Toronto Cookies request.",
        """<h1 id="thx-h">Thanks, your request is in</h1><p class="lede" id="thx-p">We'll reply within one business day with the bakery, delivery date, final price and a secure payment link. Nothing is ordered until you approve and pay.</p><p><a href="/">Back to home</a></p>
<script>(function(){var m=location.search.match(/[?&]paid=([\\w-]+)/);
if(m){document.getElementById('thx-h').textContent='Payment received, thank you!';
document.getElementById('thx-p').textContent='Your receipt is on its way by email. Within one business day we will email you to confirm the bakery, delivery date and any recipient details, then place your order.';}
window.addEventListener('load',function(){if(window.posthog){posthog.capture(m?'order_paid_thanks_viewed':'quote_thanks_viewed',{package:m?m[1]:null});}});})();</script>""", [])

    # FAQ
    out["faq/index.html"] = page("/faq/", "Corporate Cookie Gift FAQ: Prices, Deadlines & Delivery",
        "Answers about corporate and holiday cookie gifts in Toronto: prices, 2026 order deadlines, multi-address delivery, nut-free options, logo cookies and payment.",
        f"<h1>Frequently asked questions</h1>{faq_html(FAQ)}<p class='after-list'><a class='btn' href='/order/'>Start an order</a></p>",
        [faq_schema(FAQ)], [("/", "Home"), ("/faq/", "FAQ")])

    # About
    out["about/index.html"] = page("/about/", "About Toronto Cookies | Corporate Cookie Gifting Concierge",
        "Toronto Cookies is a Toronto-based corporate cookie gifting concierge. We source from licensed local bakeries and coordinate cards and delivery for offices.",
        """<h1>About Toronto Cookies</h1>
<p class="lede">Toronto Cookies is a Toronto-based gifting concierge for offices that want to send great cookies without managing ten bakery checkouts.</p>
<p>We don't run a kitchen. We choose the right established Toronto bakery for each order (gourmet boxes, nut-free facilities, logo-cookie specialists), then handle the cards, scheduling and delivery coordination. You get one point of contact and one invoice.</p>
<p>Questions or partnership ideas from Toronto bakeries are welcome at the email below.</p>""",
        [{"@type": "AboutPage", "url": BASE + "/about/", "about": {"@id": BASE + "/#org"}}], [("/", "Home"), ("/about/", "About")])

    # Guide: deadlines (AEO)
    g = "/guides/holiday-cookie-gift-deadlines-toronto-2026/"
    body = f"""<p class="crumbs"><a href="/">Home</a> › Guides › 2026 holiday deadlines</p>
<h1>When to order holiday cookie gifts in Toronto (2026 deadlines)</h1>
<p class="lede"><strong>Short answer:</strong> for corporate cookie gifts in Toronto, order by {CONFIG['ORDER_BY']} to have them delivered by {CONFIG['DELIVER_BY']}, before most offices close for the holidays. Custom logo cookies need more lead time: aim for 2 weeks, although some Toronto bakeries offer 48-hour rush printing for a fee of about 20%.</p>
<table><thead><tr><th>What you're sending</th><th>Typical lead time</th><th>Order by (for Dec 18 delivery)</th></tr></thead><tbody>
<tr><td>Gourmet cookie gift boxes</td><td>2–5 business days</td><td>Dec 9–11</td></tr>
<tr><td>Office trays for a party</td><td>3–5 business days</td><td>3–5 days before the event</td></tr>
<tr><td>10+ boxes to different addresses</td><td>5–7 business days</td><td>Dec 9</td></tr>
<tr><td>Printed logo cookies</td><td>3–9 business days (48h rush at some bakeries)</td><td>Dec 4–8</td></tr>
<tr><td>Hand-iced custom designs</td><td>1–3 weeks</td><td>As early as possible</td></tr>
</tbody></table>
<h2>Why December fills up fast</h2>
<p>Toronto bakeries run limited holiday batches and cap custom orders in December, and courier slots get tight in the week before the holidays. Booking early protects both your date and your choice of bakery.</p>
<h2>Checklist before you order</h2>
<ul><li>Recipient list with names, addresses and buzzer codes</li><li>Card message (one for all, or personalized)</li><li>Dietary needs (nut-free offices, vegan recipients)</li><li>Budget per recipient</li><li>Logo file (SVG or high-res PNG) for logo cookies</li></ul>
<p><a class="btn" href="/order/">Book your holiday cookie gifts</a></p>
<p class="small">Lead times are based on Toronto bakeries' published policies, checked November 23, 2026.</p>"""
    out["guides/holiday-cookie-gift-deadlines-toronto-2026/index.html"] = page(g,
        "When to Order Holiday Cookie Gifts in Toronto: 2026 Deadlines",
        "Order corporate cookie gifts in Toronto by Dec 9, 2026 for delivery by Dec 18. Lead times for gift boxes, office trays, multi-address and logo cookies.",
        body, [{"@type": "Article", "headline": "When to order holiday cookie gifts in Toronto (2026 deadlines)",
                "datePublished": TODAY, "dateModified": TODAY, "author": {"@id": BASE + "/#org"},
                "publisher": {"@id": BASE + "/#org"}, "mainEntityOfPage": BASE + g, "image": BASE + "/assets/logo.png"},
               faq_schema([FAQ[3]])], [("/", "Home"), (g, "2026 holiday cookie gift deadlines")])

    # Guide: price guide (AEO)
    g = "/custom-cookie-prices-toronto/"
    body = f"""<p class="crumbs"><a href="/">Home</a> › Toronto cookie price guide</p>
<h1>How much do custom and gift cookies cost in Toronto? (2026 price guide)</h1>
<p class="lede"><strong>Short answer:</strong> in Toronto, hand-decorated custom sugar cookies usually cost about $54 to $120 per dozen. Printed logo cookies run about $3.50 to $5 each at volume (often 50 minimum), and gourmet cookie gift boxes cost about $33 to $66 for 6 to 25 cookies.</p>
<table><thead><tr><th>Type</th><th>Typical Toronto price (CAD)</th><th>Minimums / notes</th></tr></thead><tbody>
<tr><td>Custom decorated sugar cookies (simple)</td><td>$54–$85 per dozen</td><td>Often 1–1.5 dozen minimum</td></tr>
<tr><td>Custom decorated sugar cookies (detailed)</td><td>$72–$120+ per dozen</td><td>Metallic or florals cost more</td></tr>
<tr><td>Printed logo cookies</td><td>$3.49–$4.99 each</td><td>Usually 50 per design</td></tr>
<tr><td>Logo cookie gift box (6)</td><td>about $25–$45</td><td>Holiday editions sell out</td></tr>
<tr><td>Gourmet cookie gift box (6)</td><td>about $33–$48</td><td>Same-day delivery at some bakeries</td></tr>
<tr><td>Gourmet cookie gift box (18–25)</td><td>about $54–$66</td><td>Plus delivery</td></tr>
<tr><td>Cookie towers and baskets</td><td>about $70–$225</td><td>Premium client gifts</td></tr>
</tbody></table>
<h2>What drives the price</h2>
<ul><li><strong>Design complexity:</strong> colours, shapes, lettering and metallic details.</li><li><strong>Packaging:</strong> individual heat-sealing, boxes, ribbons and cards.</li><li><strong>Rush:</strong> under one week's notice often adds up to 20%.</li><li><strong>Delivery:</strong> multiple addresses add courier cost per stop.</li></ul>
<h2>Where Toronto Cookies fits</h2>
<p>Our packages bundle the cookies, card and City of Toronto delivery into one price: <a href="/holiday-cookie-gift-box-toronto/">$59 single gift</a>, <a href="/office-cookie-tray-toronto/">$129 office tray</a>, <a href="/client-cookie-gift-pack-toronto/">$590 for ten clients</a>. <a href="/logo-cookies-toronto/">Logo cookies</a> are the bakery's quote plus 20% (minimum $79).</p>
<p class="small">Ranges compiled from Toronto bakeries' public price lists, checked November 23, 2026. Prices change; confirm before ordering.</p>"""
    pfaq = [("How much do custom cookies cost per dozen in Toronto?",
             "Most Toronto custom cookie bakers charge about $54 to $85 per dozen for simple designs and $72 to $120 or more per dozen for detailed designs, as of November 2026."),
            ("How much are logo cookies in Toronto?",
             "Printed logo cookies typically cost $3.49 to $4.99 each at volume in Toronto, usually with a 50-cookie minimum per design.")]
    out["custom-cookie-prices-toronto/index.html"] = page(g,
        "Custom Cookie Prices in Toronto (2026): Per Dozen, Logo & Gift Boxes",
        "Toronto custom cookies cost about $54–$120 per dozen; logo cookies $3.49–$4.99 each; gift boxes $33–$66. 2026 price guide with minimums and lead times.",
        body, [{"@type": "Article", "headline": "How much do custom and gift cookies cost in Toronto? (2026 price guide)",
                "datePublished": TODAY, "dateModified": TODAY, "author": {"@id": BASE + "/#org"},
                "publisher": {"@id": BASE + "/#org"}, "mainEntityOfPage": BASE + g, "image": BASE + "/assets/logo.png"},
               faq_schema(pfaq)], [("/", "Home"), (g, "Toronto cookie price guide")])

    # 404
    out["404.html"] = page("/404.html", "Page not found | Toronto Cookies", "This page doesn't exist.",
        "<h1>That page crumbled</h1><p>Try the <a href='/'>home page</a>, our <a href='/corporate-cookie-gifts-toronto/'>corporate gifts</a> or <a href='/order/'>order form</a>.</p>", [])
    return out

CSS = """@font-face{font-family:Poppins;font-style:normal;font-weight:400;font-display:swap;src:url("/assets/fonts/poppins-400.woff2") format("woff2")}
@font-face{font-family:Poppins;font-style:normal;font-weight:600;font-display:swap;src:url("/assets/fonts/poppins-600.woff2") format("woff2")}
@font-face{font-family:Poppins;font-style:normal;font-weight:700;font-display:swap;src:url("/assets/fonts/poppins-700.woff2") format("woff2")}
:root{--cream:#fbf6f1;--ink:#161616;--pink:#d4145a;--pink-d:#b01048;--muted:#3d3d3d;--line:#eadfd4;--sans:Poppins,sans-serif;--container:1440px;--gutter:clamp(20px,4vw,64px);--section:clamp(40px,5vw,68px)}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;font:16px/1.55 var(--sans);background:var(--cream);color:var(--ink)}
img{max-width:100%;height:auto;display:block}
a{color:var(--ink)}
:focus-visible{outline:3px solid var(--pink);outline-offset:3px}
.wrap{width:100%;max-width:var(--container);margin-inline:auto;padding-inline:var(--gutter)}
.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:#fff;padding:10px 14px;z-index:9}
.announce{background:var(--pink);color:#fff}
.announce p{margin:0;padding:12px 0;font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase}
.site-header{background:var(--cream);border-bottom:1px solid var(--line)}
.site-header .wrap{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 28px;padding-top:22px;padding-bottom:22px}
.brand{font-family:var(--sans);font-weight:700;font-size:28px;letter-spacing:-.03em;text-decoration:none;color:var(--ink);line-height:1}
.site-header nav{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px}
.site-header nav a{text-decoration:none;font-weight:600;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink);padding:12px 4px;min-height:44px}
.site-header nav a[aria-current]{text-decoration:underline;text-underline-offset:6px}
.site-header nav a[href="/order/"]{background:var(--ink);color:#fff;border-radius:2px;padding:14px 22px}
.page{padding-top:44px;padding-bottom:var(--section)}
h1,h2,h3{font-family:var(--sans);font-weight:700;letter-spacing:-.03em;line-height:1.02;color:var(--ink)}
h1{font-size:clamp(40px,4.6vw,68px);margin:0 0 28px;max-width:none}
h2{font-size:clamp(32px,4vw,52px);margin:48px 0 24px}
:is(.wrap,.page) > h2:first-child{margin-top:0}
h3{font-size:26px;margin:0 0 .25em}
.lede,.section-lead,.upsell p,.page > p:not(.notice){font-size:18px;max-width:65ch}
.lede,.section-lead,.page > .lede{margin:0 0 28px}
.section-lead{margin-top:0}
.page > p:not(.notice):not(.lede):not(.after-list){margin:0 0 20px}
.after-list{margin:32px 0 0}
.hero{padding:32px 0 20px}
.hero-grid{display:grid;gap:28px;align-items:center}
.hero-visual{margin:0}
.hero-visual img{width:100%;height:220px;object-fit:cover;object-position:68% 42%}
.hero h1{font-size:clamp(36px,3.4vw,56px);max-width:none;margin-bottom:24px}
.proof{padding:20px 0}
.proof p{margin:0;padding:12px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);font-size:15px;font-weight:600;max-width:none}
.cta-row{display:flex;flex-wrap:wrap;gap:12px;margin-top:18px}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:52px;background:var(--pink);color:#fff;padding:14px 22px;border-radius:2px;text-decoration:none;font-weight:700;letter-spacing:.04em;text-transform:uppercase;font-size:14px;border:2px solid var(--pink);cursor:pointer}
.btn:hover{background:var(--pink-d);border-color:var(--pink-d);color:#fff}
.btn-ghost{background:transparent;color:var(--ink);border-color:var(--ink)}
.btn-ghost:hover{background:var(--ink);color:#fff}
.btn-small{min-height:46px;padding:10px 14px;font-size:12px}
.trust{padding-top:var(--section);padding-bottom:var(--section)}
.trust-row{list-style:none;margin:0;padding:8px 0 4px;display:grid;gap:16px}
.trust-row li{display:grid;gap:4px}
.trust-row strong{font-size:14px;letter-spacing:.06em;text-transform:uppercase}
.trust-row span{color:var(--muted);font-size:15px}
.band,.how,.upsell,.faq-teaser{padding-top:var(--section);padding-bottom:var(--section)}
.grid{display:grid;grid-template-columns:1fr;gap:36px}
.card{background:transparent;display:flex;flex-direction:column}
.card img{width:100%;aspect-ratio:1/1;object-fit:cover}
.card-body{display:flex;flex-direction:column;gap:10px;padding:24px 4px 8px}
.card h3{font-size:22px;text-transform:uppercase;letter-spacing:-.02em}
.card h3 a{color:var(--ink);text-decoration:none}
.card h3 a:hover{text-decoration:underline}
.card p{margin:0}
.price{font-family:var(--sans);font-size:32px;font-weight:700;margin:0}
.price span{font-family:var(--sans);font-size:13px;font-weight:600;letter-spacing:.08em}
.card .btn{margin-top:6px;align-self:flex-start}
.steps{list-style:none;margin:0;padding:0;display:grid;gap:18px}
.steps li{padding-top:8px}
.steps p{margin:.3em 0 0;color:var(--muted)}
.upsell-grid{display:grid;gap:22px;align-items:center}
.upsell-grid img{width:100%;aspect-ratio:1/1;object-fit:cover}
.deadline{padding-top:var(--section);padding-bottom:var(--section)}
.notice{background:#fff;border:2px solid var(--ink);padding:28px 32px;margin:0;max-width:none}
.product-intro{display:grid;gap:22px;align-items:center;margin-bottom:12px}
.product-photo{margin:0}
.product-photo img{width:100%;aspect-ratio:1/1;object-fit:cover}
.text-link{font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:14px}
table{border-collapse:collapse;width:100%;background:#fff;margin:16px 0;border:2px solid var(--ink)}
th,td{border-bottom:1px solid var(--line);padding:16px 20px;text-align:left;vertical-align:top}
th{font-size:13px;letter-spacing:.08em;text-transform:uppercase}
details{background:#fff;border:2px solid var(--ink);border-bottom:0;margin:0;padding:0}
details:last-of-type{border-bottom:2px solid var(--ink)}
summary{font-weight:700;cursor:pointer;list-style:none;min-height:64px;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 24px}
summary::-webkit-details-marker{display:none}
summary::after{content:"+";flex:none;font-size:28px;font-weight:400;line-height:1}
details[open] summary::after{content:"−"}
details p{margin:0;padding:0 24px 20px;max-width:none}
.order{display:grid;gap:16px;max-width:640px}
.order label{display:grid;gap:8px;font-weight:600}
.order input,.order select,.order textarea{font:16px/1.4 var(--sans);padding:14px 16px;border:2px solid var(--ink);border-radius:0;background:#fff;min-height:48px}
.hp{position:absolute;left:-5000px}
.small,.fine{font-size:14px}
.crumbs{font-size:13px;letter-spacing:.06em;text-transform:uppercase}
.buy{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.site-footer{background:#111;color:#fbf6f1;padding:64px 0 40px}
.site-footer a{color:#fbf6f1}
.footer-brand{font-family:var(--sans);font-size:36px;font-weight:700;margin:0 0 8px;letter-spacing:-.03em}
.site-footer nav{display:flex;flex-wrap:wrap;gap:10px 18px;margin:18px 0}
.site-footer nav a{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;text-underline-offset:4px}
.site-footer .fine{color:#fbf6f1}
.order-steps li{margin:8px 0}
@media(min-width:800px){
.site-header nav{gap:10px 32px}
.trust-row{grid-template-columns:repeat(4,1fr);gap:22px}
.grid{grid-template-columns:1fr 1fr;gap:36px}
.steps-3{grid-template-columns:1fr 1fr 1fr;gap:32px}
.hero{padding:40px 0 24px}
.hero-grid{grid-template-columns:1.15fr .85fr;gap:40px}
.hero-visual img{height:min(360px,42vh)}
.upsell-grid{grid-template-columns:1fr 1fr;gap:64px}
.product-intro{grid-template-columns:1.05fr .95fr;gap:48px}
.product-photo{order:2}
}
@media(min-width:1280px){
.grid{grid-template-columns:repeat(4,1fr);gap:36px}
}
"""

JS = """(function(){
  // Prefill the package on /order/?package=...
  var sel=document.getElementById('package');
  if(sel){var m=location.search.match(/[?&]package=([\\w-]+)/);if(m){sel.value=m[1];}}
  // Lightweight PostHog events (autocapture also records clicks)
  document.addEventListener('click',function(ev){
    var a=ev.target.closest('[data-track]');
    if(a&&window.posthog){posthog.capture(a.getAttribute('data-track'),{package:a.getAttribute('data-package')||null,href:a.getAttribute('href')});}
  });
  var f=document.querySelector('form[data-track-form]');
  if(f){f.addEventListener('submit',function(){
    if(window.posthog){var d=new FormData(f);posthog.capture(f.getAttribute('data-track-form'),{package:d.get('package'),area:d.get('area'),dietary:d.get('dietary')});}
  });}
})();
"""

ROBOTS = f"""# torontocookies.ca: search and AI answer engines welcome
User-agent: *
Allow: /
Disallow: /thanks/
Disallow: /_legacy-2022/

User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Bingbot
Allow: /

Sitemap: {BASE}/sitemap.xml
"""

ROBOTS_STAGING = """# Staging preview (staging.torontocookies.ca): never index
User-agent: *
Disallow: /
"""

HTACCESS = r"""# torontocookies.ca: Apache config (Hostinger)
Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html

<IfModule mod_rewrite.c>
RewriteEngine On

# Block repo internals, the 2022 backup, and markdown (including CREDITS.md) from the web
RewriteRule ^(\.git|\.github|_legacy-2022)(/|$) - [F,L,NC]
RewriteRule ^(build\.py|README\.md|.*\.md)$ - [F,L,NC]

# The staging subdomain's folder may sit inside public_html: hide it on the production host
RewriteCond %{HTTP_HOST} !^staging\. [NC]
RewriteRule ^staging(/|$) - [R=404,L,NC]

# Staging subdomain gets its own robots.txt (Disallow everything)
RewriteCond %{HTTP_HOST} ^staging\. [NC]
RewriteRule ^robots\.txt$ /robots-staging.txt [L]

# www to the bare domain. Do not also force HTTPS for torontocookies.ca here.
# Hostinger's Force HTTPS already 301s http://torontocookies.ca/ at the CDN.
# Testing %{HTTPS} !=on and X-Forwarded-Proto on LiteSpeed returns 500 for that request.
RewriteCond %{HTTP_HOST} ^www\.torontocookies\.ca$ [NC]
RewriteRule ^(.*)$ https://torontocookies.ca/$1 [R=301,L]

# Old 2022 page URL, if anything still links to it
RewriteRule ^index\.htm$ / [R=301,L]
</IfModule>

<IfModule mod_headers.c>
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set X-Frame-Options "SAMEORIGIN"
Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
# Staging must never be indexed
<If "%{HTTP_HOST} =~ /^staging\./i">
Header always set X-Robots-Tag "noindex, nofollow"
</If>
<FilesMatch "^robots-staging\.txt$">
Header always set X-Robots-Tag "noindex"
</FilesMatch>
<FilesMatch "\.(css|js|png|jpg|svg|ico|webp)$">
Header set Cache-Control "public, max-age=604800"
</FilesMatch>
<FilesMatch "\.(html|xml|txt)$">
Header set Cache-Control "public, max-age=300"
</FilesMatch>
</IfModule>

<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript text/plain application/xml image/svg+xml application/ld+json
</IfModule>
"""

def llms_txt():
    lines = ["# Toronto Cookies", "",
             "> Corporate and holiday cookie gifting concierge for Toronto offices. We source gourmet, nut-free and custom logo cookies from licensed Toronto bakeries and deliver to every recipient. We do not bake or handle food ourselves.", "",
             "Key facts:",
             "- Single holiday cookie gift box delivered in Toronto: $59 CAD",
             "- Office holiday cookie tray (24-30 cookies): $129 CAD",
             "- Client Gift Pack, 10 boxes to 10 Toronto addresses with cards: $590 CAD",
             "- Custom logo cookies: bakery quote + 20% concierge fee, minimum $79 CAD",
             "- City of Toronto delivery included; rest of GTA quoted",
             f"- 2026 holiday deadline: order by {CONFIG['ORDER_BY']} for delivery by {CONFIG['DELIVER_BY']}",
             "- Payment by card via Stripe after the order is confirmed; nothing is ordered before payment", "",
             "## Pages",
             f"- [Corporate cookie gifts Toronto]({BASE}/corporate-cookie-gifts-toronto/): packages, prices, uses",
             ] + [f"- [{p['name']}]({BASE}/{p['slug']}/): {p['short']}" for p in PACKAGES] + [
             f"- [FAQ]({BASE}/faq/): prices, deadlines, delivery, allergies, payment",
             f"- [2026 holiday cookie gift deadlines]({BASE}/guides/holiday-cookie-gift-deadlines-toronto-2026/)",
             f"- [Toronto custom cookie price guide]({BASE}/custom-cookie-prices-toronto/)",
             f"- [Order or request a quote]({BASE}/order/)", "",
             f"Contact: {CONFIG['ORDER_EMAIL']}", ""]
    return "\n".join(lines)

def sitemap(paths):
    urls = "".join(f"<url><loc>{BASE}{p}</loc><lastmod>{TODAY}</lastmod></url>\n" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'

WORKFLOW = r"""name: Site QA
on:
  pull_request:
    branches: [main]
  push:
    branches: [staging]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build-and-check:
    name: Build + structure checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Generated files are up to date
        run: |
          python3 build.py
          git diff --exit-code || (echo "::error::Run 'python3 build.py' and commit the output" && exit 1)
      - name: Structure, schema and internal links
        run: python3 build.py --check

  html-validate:
    name: HTML validation (W3C Nu)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Cyb3r-Jak3/html5validator-action@v7.2.0
        with:
          root: .
          blacklist: _legacy-2022 .github
          format: text

  links:
    name: Broken links (lychee)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Internal links (blocking)
        uses: lycheeverse/lychee-action@v2
        with:
          args: --offline --no-progress --root-dir "${{ github.workspace }}" --exclude-path _legacy-2022 './**/*.html'
          fail: true
      - name: External links (report only)
        uses: lycheeverse/lychee-action@v2
        continue-on-error: true
        with:
          args: --no-progress --max-retries 2 --timeout 20 --accept 200,201,204,301,302,403,429 --exclude 'formsubmit\.co' --exclude 'posthog\.com' --exclude 'torontocookies\.ca' --exclude-path _legacy-2022 './**/*.html'
          fail: false

  lighthouse:
    name: Lighthouse CI (advisory)
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - uses: treosh/lighthouse-ci-action@v12
        with:
          configPath: ./.github/lighthouserc.json
          uploadArtifacts: true
          temporaryPublicStorage: true
"""

# The Hostinger FTP user (u916429614) is rooted at /home/u916429614, not public_html.
# server-dir must be domains/torontocookies.ca/public_html/staging/ so uploads land in the
# subdomain document root. Never ./, /, public_html/, or domains/torontocookies.ca/public_html/.
# The sync state file is server-dir + state-name, so it stays inside that staging folder.
# dangerous-clean-slate stays false: the action must not wipe the server folder.
DEPLOY_STAGING = r"""name: Deploy staging
on:
  push:
    branches: [staging]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  ftp:
    name: FTPS deploy to staging
    runs-on: ubuntu-latest
    steps:
      - name: Check FTP secrets
        id: ftp
        env:
          FTP_SERVER: ${{ secrets.FTP_SERVER }}
          FTP_USERNAME: ${{ secrets.FTP_USERNAME }}
          FTP_PASSWORD: ${{ secrets.FTP_PASSWORD }}
        run: |
          if [ -z "$FTP_SERVER" ] || [ -z "$FTP_USERNAME" ] || [ -z "$FTP_PASSWORD" ]; then
            echo "::notice::FTP secrets are not set (FTP_SERVER, FTP_USERNAME, FTP_PASSWORD). Skipping the staging deploy."
            echo "ready=false" >> "$GITHUB_OUTPUT"
          else
            echo "FTP secrets are present. Deploying into domains/torontocookies.ca/public_html/staging/ only."
            echo "ready=true" >> "$GITHUB_OUTPUT"
          fi

      - uses: actions/checkout@v4
        if: steps.ftp.outputs.ready == 'true'

      - name: Deploy into domains/torontocookies.ca/public_html/staging over FTPS
        if: steps.ftp.outputs.ready == 'true'
        uses: SamKirkland/FTP-Deploy-Action@v4.4.0
        with:
          server: ${{ secrets.FTP_SERVER }}
          username: ${{ secrets.FTP_USERNAME }}
          password: ${{ secrets.FTP_PASSWORD }}
          protocol: ftps
          port: 21
          local-dir: ./
          # Relative to /home/u916429614. Never ./, /, public_html/, or the production public_html root.
          server-dir: domains/torontocookies.ca/public_html/staging/
          # Stored inside that staging folder. Deletes only paths listed there.
          state-name: .ftp-deploy-sync-state.json
          dangerous-clean-slate: false
          exclude: |
            **/.git*
            **/.git*/**
            **/node_modules/**
            **/.github/**
            **/build.py
            **/*.md
            **/_legacy-2022/**
"""

LHCI = json.dumps({"ci": {
    "collect": {"staticDistDir": ".", "url": ["/index.html", "/order/index.html", "/client-cookie-gift-pack-toronto/index.html"], "numberOfRuns": 1},
    "assert": {"assertions": {
        "categories:performance": ["warn", {"minScore": 0.85}],
        "categories:accessibility": ["warn", {"minScore": 0.9}],
        "categories:best-practices": ["warn", {"minScore": 0.9}],
        "categories:seo": ["error", {"minScore": 0.9}]}}}}, indent=2) + "\n"

PR_TEMPLATE = """## What changed
<!-- One or two lines. Link the Notion plan item if relevant. -->

## QA checklist (staging.torontocookies.ca before merging to main)
### Automated (must be green)
- [ ] Build + structure checks (`python3 build.py --check`)
- [ ] HTML validation (W3C Nu)
- [ ] Internal links (lychee)
- [ ] Lighthouse SEO ≥ 0.90 (performance/accessibility are advisory)

### Manual
- [ ] Home, corporate hub, 4 package pages, order, FAQ, guides load on desktop and mobile
- [ ] Prices match the plan: $59 / $129 / $590 / bakery cost + 20% (min $79)
- [ ] Order form submits and lands on /thanks/ (FormSubmit activated for the order inbox)
- [ ] Pay buttons: Stripe links only where approved; otherwise "Request this package" goes to /order/
- [ ] Staging only: response has `X-Robots-Tag: noindex, nofollow` and `/robots.txt` is `Disallow: /`
- [ ] Production robots.txt allows crawlers and lists the sitemap
- [ ] Rich Results Test passes for one package page (Product + FAQPage + BreadcrumbList)
- [ ] PostHog: a pageview from this build shows up in project 593979 with `site_env`
- [ ] No claims we can't back up (no named bakery partners without agreement; allergen info from bakery labels)

## After merge
- [ ] Hostinger deployed `main` to torontocookies.ca (check the live site)
- [ ] Submit/refresh the sitemap in Search Console and Bing Webmaster Tools
"""

README = """# torontocookies.ca

Static site for **Toronto Cookies**, a corporate and holiday cookie gifting concierge in Toronto.

* `build.py` generates every page and config file. Edit it, run `python3 build.py`, commit the output.
* `python3 build.py --check` runs the same structure checks as CI.
* Branches: work on `staging` (deploys to staging.torontocookies.ca, noindex). Open a PR to `main`; merging deploys production via Hostinger Git auto-deploy.
* Stripe: set `STRIPE_LINKS` in `build.py` once payment links are approved. Empty = buttons go to the order form.
* Form: FormSubmit.co posts to `CONFIG["ORDER_EMAIL"]` (first submission needs a one-time activation click).
* Analytics: PostHog project 593979, events `package_cta_clicked`, `pay_link_clicked`, `quote_submitted`, `quote_thanks_viewed`; property `site_env` = production|staging.
* `_legacy-2022/` is the backup of the 2022 page (blocked from the web by `.htaccess`).
* Photo and type credits are in `CREDITS.md`, also blocked by the markdown rule.
* Bare-domain HTTPS is Hostinger's Force HTTPS setting. `.htaccess` only redirects `www` to the apex, so `staging.*` is left alone (noindex header and `robots-staging.txt` still apply there).
* A push to `staging` deploys into `domains/torontocookies.ca/public_html/staging/` over FTPS (the FTP account is rooted at the home directory). Missing secrets skip the deploy.
"""

CREDITS = """# Credits

Photographs and typefaces used on torontocookies.ca. This file is blocked from the web by the `.htaccess` rule that forbids `*.md`.

## Photographs

Most photographs are used under the [Unsplash License](https://unsplash.com/license). The home hero is used under the [Pexels License](https://www.pexels.com/license/). The iced sugar cookies are from Wikimedia Commons under CC BY-SA 3.0. This WebP crop is shared under the same licence.

| File | What it shows | Source |
| --- | --- | --- |
| `assets/hero.webp` | Wrapped gift boxes with satin ribbons | https://www.pexels.com/photo/1303081/ — [Pexels License](https://www.pexels.com/license/) (commercial use, no attribution required). File: https://images.pexels.com/photos/1303081/pexels-photo-1303081.jpeg |
| `assets/gift-box.webp` | A stack of chocolate chip cookies | https://images.unsplash.com/photo-1548365328-8c6db3220e4c |
| `assets/office-tray.webp` | Cookies in a parchment-lined bowl | https://images.unsplash.com/photo-1558961363-fa8fdf82db35 — Mae Mu |
| `assets/client-gifts.webp` | Gingerbread people and snowflakes | https://images.unsplash.com/photo-1639590229762-3c9a8c98ca31 |
| `assets/logo-cookies.webp` | Iced sugar cookies with sprinkles | https://commons.wikimedia.org/wiki/File:Decorated_sugar_cookies.jpg — Julie Anne Workman, CC BY-SA 3.0 |

## Type

Poppins, from Google Fonts, used under the SIL Open Font License. The Latin woff2 files (400, 600, 700) are self-hosted in `assets/fonts/`.
"""

def write(rel, content, mode="w"):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8", newline="\n") as f:
        f.write(content)

def build():
    pages = build_pages()
    for rel, html_ in pages.items():
        write(rel, html_)
    write("assets/site.css", CSS)
    write("assets/site.js", JS)
    write("robots.txt", ROBOTS)
    write("robots-staging.txt", ROBOTS_STAGING)
    write(".htaccess", HTACCESS)
    write("llms.txt", llms_txt())
    paths = ["/" + (r[:-len("index.html")] if r.endswith("index.html") else r) for r in pages
             if r not in ("404.html", "thanks/index.html")]
    paths = sorted(paths, key=lambda p: (p != "/", p))
    write("sitemap.xml", sitemap(paths))
    write(".github/workflows/qa.yml", WORKFLOW)
    write(".github/workflows/deploy-staging.yml", DEPLOY_STAGING)
    write(".github/lighthouserc.json", LHCI)
    write(".github/pull_request_template.md", PR_TEMPLATE)
    write("README.md", README)
    write("CREDITS.md", CREDITS)
    write("_legacy-2022/index.html", LEGACY_HTML)
    print("built %d pages" % len(pages))

def check():
    errors = []
    req = ["index.html", "404.html", ".htaccess", "robots.txt", "robots-staging.txt", "sitemap.xml", "llms.txt",
           "CREDITS.md", "assets/site.css", "assets/site.js", "assets/logo.png",
           "assets/hero.webp", "assets/hero-800.webp", "assets/gift-box.webp", "assets/office-tray.webp", "assets/client-gifts.webp", "assets/logo-cookies.webp",
           "assets/fonts/poppins-400.woff2", "assets/fonts/poppins-600.woff2", "assets/fonts/poppins-700.woff2",
           "_legacy-2022/index.html", "_legacy-2022/assets/torontocookies.jpg"]
    for r in req:
        if not os.path.exists(os.path.join(ROOT, r)):
            errors.append("missing " + r)
    htmls = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in (".git", ".github", "_legacy-2022", "node_modules")]
        htmls += [os.path.join(d, f) for f in files if f.endswith(".html")]
    for fpath in htmls:
        rel = os.path.relpath(fpath, ROOT)
        s = open(fpath, encoding="utf-8").read()
        if s.count("<h1") != 1: errors.append(f"{rel}: expected exactly one <h1>")
        t = re.search(r"<title>(.*?)</title>", s)
        if not t or not (15 <= len(html.unescape(t.group(1))) <= 70): errors.append(f"{rel}: title length")
        dm = re.search(r'<meta name="description" content="(.*?)">', s)
        if not dm or not (20 <= len(html.unescape(dm.group(1))) <= 170): errors.append(f"{rel}: description length {len(dm.group(1)) if dm else 0}")
        if '<link rel="canonical"' not in s: errors.append(f"{rel}: no canonical")
        for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try: json.loads(blk)
            except Exception as ex: errors.append(f"{rel}: bad JSON-LD {ex}")
        if "posthog.init(" not in s: errors.append(f"{rel}: no PostHog snippet")
        for href in re.findall(r'(?:href|src)="(/[^"#?]*)', s):
            target = os.path.join(ROOT, href.lstrip("/"))
            if href.endswith("/"): target = os.path.join(target, "index.html")
            if not os.path.exists(target): errors.append(f"{rel}: broken internal link {href}")
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    for loc in re.findall(r"<loc>(.*?)</loc>", sm):
        p = loc.replace(BASE, "").lstrip("/")
        if not os.path.exists(os.path.join(ROOT, p, "index.html") if (p == "" or p.endswith("/")) else os.path.join(ROOT, p)):
            errors.append("sitemap points to missing page " + loc)
    if "Disallow: /\n" not in open(os.path.join(ROOT, "robots-staging.txt")).read():
        errors.append("robots-staging.txt must disallow everything")
    if re.search(r"^Disallow: /\s*$", open(os.path.join(ROOT, "robots.txt")).read(), re.M):
        errors.append("production robots.txt blocks the whole site")
    if errors:
        print("QA FAILED:\n  " + "\n  ".join(errors)); sys.exit(1)
    print(f"QA OK: {len(htmls)} pages, schema, links, sitemap, robots")

if __name__ == "__main__":
    check() if "--check" in sys.argv else build()
