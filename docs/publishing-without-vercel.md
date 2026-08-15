# Publishing without Vercel

Saved for future reference: how to keep this site publishing if it moves off
Vercel onto Hostinger's shared plan (or any other plain static host).

## The one thing that changes

The site is static, so **hosting** it anywhere is trivial: upload the contents
of `dist/` to `public_html`. The public pages, the `/admin` panel and the
`.htaccess` 404 rule all work on Apache exactly as they do on Vercel.

What does *not* move is the **build**. Something has to run:

```
python3 build.py      # sync.py pulls Supabase -> SQLite -> renders dist/
```

Vercel does that today, triggered by the Publish button in `/admin` via a
deploy hook. Hostinger's shared plan runs PHP only — no Python, no build step —
so the Publish button would fire into nothing.

**A static host is not enough. You need a build service.** GitHub Actions is
one, and it's free.

## The shape of the fix

```
   /admin (browser)  ──writes──►  Supabase
                                     │
                                     │ build.py reads
                                     ▼
                            GitHub Actions runner
                                     │ FTP upload
                                     ▼
                            Hostinger public_html
```

Hostinger credentials live in GitHub's encrypted secrets, never in the repo.

## Three ways to trigger it

Pick any or all.

### 1. On push

A code change rebuilds and uploads. Zero extra work; you get this for free with
the workflow below.

### 2. On a schedule

The workflow runs every 30 minutes and republishes if Supabase content changed.
The client edits, and it goes live within half an hour with nobody doing
anything.

**This is usually enough.** For a brochure site whose content changes a few
times a month, the wait is irrelevant and there is nothing to maintain.

### 3. On the Publish button

To make Publish instant again it must call GitHub's API, which needs a token.
That token *cannot* sit in `admin/config.js` — that file is public, and anyone
could take it and push to the repo.

The clean way is a small **Supabase Edge Function**: the admin calls it with
the signed-in user's session, the function holds the GitHub token as a
server-side secret and triggers the workflow. About 20 lines.

Worth it only if the client will be impatient about seeing changes live.

## The workflow file

Save as `.github/workflows/publish.yml`.

```yaml
name: Build and publish

on:
  push:
    branches: [main]
  schedule:
    - cron: "*/30 * * * *"     # every 30 minutes
  workflow_dispatch:            # manual, and what the Edge Function calls
  repository_dispatch:
    types: [publish]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install jinja2==3.1.2

      - name: Build from Supabase
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
        run: python3 build.py

      - name: Upload to Hostinger
        uses: SamKirkland/FTP-Deploy-Action@v4.3.5
        with:
          server: ${{ secrets.FTP_HOST }}
          username: ${{ secrets.FTP_USER }}
          password: ${{ secrets.FTP_PASSWORD }}
          local-dir: ./dist/
          server-dir: /public_html/
```

### Secrets to add

GitHub repo → Settings → Secrets and variables → Actions:

| Secret | Where it comes from |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_ANON_KEY` | same page, the publishable key |
| `FTP_HOST` | Hostinger → Files → FTP Accounts |
| `FTP_USER` | same |
| `FTP_PASSWORD` | same |

`sync.py` falls back to reading `admin/config.js` if the two Supabase env vars
are absent, so those two are belt-and-braces rather than strictly required.

## Also do this on the move

- Set `DEPLOY_HOOK = ""` in `admin/config.js` so the Publish button hides
  instead of sitting there doing nothing (unless you build the Edge Function).
- Point the domain's DNS at Hostinger.
- Update `seo_site_url` in `/admin` → SEO to the live address, or the canonical
  tags and sitemap will keep advertising the old one.

## Before you move at all

Vercel is currently doing the build, the hosting, the CDN and the SSL, and it
will serve a custom domain for free. Moving to Hostinger means adding GitHub
Actions and FTP secrets to get back something that already works.

If the Hostinger plan is already paid for, consider using it for email or a
different site rather than dismantling a working pipeline.

The exception worth knowing: Vercel's free Hobby plan is for non-commercial
use, and a company website is commercial. **Cloudflare Pages** is the
free, commercial-friendly equivalent — it has a build service, so `build.py`
and the Publish button both keep working, and none of this document applies.
That is a smaller move than Hostinger.
