## What changed
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
