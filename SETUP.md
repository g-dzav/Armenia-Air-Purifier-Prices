# Setup

Two accounts needed — both free tier, both yours to own. I can't create
accounts or paste in secrets for you, so this part's manual, but it's quick.

## 1. Supabase (the database)

1. Go to supabase.com, sign up, "New project". Pick any name/region, set a
   database password (save it somewhere, you likely won't need it again).
2. Once it's ready: **SQL Editor** → New query → paste the entire contents of
   [`db/schema.sql`](db/schema.sql) → Run.
3. **Project Settings → API**. You need three values:
   - `Project URL` → this is `SUPABASE_URL`
   - `anon` `public` key → safe to put directly in `docs/index.html` (that's what it's for)
   - `service_role` key → **secret**, never put this in the dashboard or commit it. Goes into GitHub Actions secrets and your local `.env` only.

## 2. GitHub (the repo + the daily cron + the dashboard hosting)

1. Create a new repo (private or public, your call — public costs nothing
   extra and makes the dashboard link work without any auth).
2. Push this project to it:
   ```bash
   git remote add origin <your-repo-url>
   git branch -M main
   git push -u origin main
   ```
3. **Repo → Settings → Secrets and variables → Actions → New repository secret**.
   Add two:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. **Repo → Settings → Pages**. Source: "Deploy from a branch", branch `main`,
   folder `/docs` (GitHub's branch-deploy option only supports `/` or `/docs`,
   never an arbitrary folder name — that's why this project's dashboard
   folder is called `docs` rather than something more descriptive). Save.
   GitHub gives you a URL like `https://<you>.github.io/<repo>/` — that's
   the link to share.
5. Edit `docs/index.html`, fill in `SUPABASE_URL` and `SUPABASE_ANON_KEY`
   at the top of the `<script>` block, commit, push.
6. **Repo → Actions tab** — the daily workflow is already there
   (`.github/workflows/daily-scrape.yml`), scheduled for 06:00 Yerevan time.
   You can also click "Run workflow" to trigger it immediately instead of
   waiting for tomorrow.

## 3. Try it

- Trigger the Actions workflow manually once, check the run logs for each
  site's product count.
- Open your GitHub Pages URL — you should see rows.
- Run the weekly manual pass locally (see README) for Zigzag/Eldorado/
  AllSell/Ozon/Homemart/Wildberries — those need a human to clear a
  challenge at least once before they'll have any data at all.

## Ongoing cost

Supabase free tier and GitHub Actions/Pages free tier both comfortably cover
a project this size (a handful of sites, once a day, small tables). Nothing
here should hit a paywall unless this grows a lot.
