# torontocookies.ca

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
* A push to `staging` deploys that folder over FTPS when `FTP_SERVER`, `FTP_USERNAME`, and `FTP_PASSWORD` are set. Missing secrets skip the deploy.
